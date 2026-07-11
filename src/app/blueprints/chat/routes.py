"""
SmartChoice AI — Chat Blueprint
Handles conversational AI endpoints.
"""
from __future__ import annotations

import uuid
from typing import Any

from flask import Blueprint, jsonify, request, session, current_app
from sqlalchemy import select

from app import db, limiter
from app.models import DecisionSession, ChatMessage, DecisionResult
from app.core.watsonx_client import generate_response
from app.core.decision_engine import (
    parse_scores_from_response,
    parse_risks_from_response,
    detect_domain_from_text,
)

chat_bp = Blueprint("chat", __name__)


def _get_or_create_session(session_id: str | None, domain: str, title: str) -> DecisionSession:
    """Retrieve existing decision session or create a new one."""
    token = session.get("user_token")
    if not token:
        token = str(uuid.uuid4())
        session["user_token"] = token
        session.permanent = True

    if session_id:
        ds = DecisionSession.query.filter_by(id=session_id, session_token=token).first()
        if ds:
            return ds

    ds = DecisionSession(
        session_token=token,
        title=title or "New Decision",
        domain=domain or "general",
    )
    db.session.add(ds)
    db.session.flush()
    return ds


@chat_bp.route("/send", methods=["POST"])
@limiter.limit("30 per minute")
def send_message():
    """
    POST /api/chat/send
    Body: {
        "message": str,
        "session_id": str | null,
        "domain": str | null,
        "title": str | null
    }
    """
    data: dict = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()

    if not user_message:
        return jsonify(error="Message is required."), 400
    if len(user_message) > 4000:
        return jsonify(error="Message too long (max 4000 characters)."), 400

    domain = data.get("domain") or detect_domain_from_text(user_message)
    session_id = data.get("session_id")
    title = data.get("title") or user_message[:60]

    try:
        dec_session = _get_or_create_session(session_id, domain, title)

        # Build conversation history from DB (SQLAlchemy 2.x compatible)
        recent_msgs = db.session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == dec_session.id)
            .order_by(ChatMessage.created_at)
            .limit(20)
        ).scalars().all()
        history = [{"role": m.role, "content": m.content} for m in recent_msgs]

        # Save user message
        user_msg = ChatMessage(
            session_id=dec_session.id,
            role="user",
            content=user_message,
        )
        db.session.add(user_msg)

        # Generate AI response
        ai_result: dict[str, Any] = generate_response(
            user_message=user_message,
            conversation_history=history,
            domain=domain,
        )

        ai_content = ai_result["content"]

        # Save AI message
        ai_msg = ChatMessage(
            session_id=dec_session.id,
            role="assistant",
            content=ai_content,
            tokens_used=ai_result.get("tokens_used", 0),
            model_used=ai_result.get("model"),
        )
        db.session.add(ai_msg)

        # Parse and persist scores/risks if present
        scores = parse_scores_from_response(ai_content)
        risks = parse_risks_from_response(ai_content)

        if scores:
            result = dec_session.result
            if not result:
                result = DecisionResult(session_id=dec_session.id)
                db.session.add(result)

            result.options = [s["name"] for s in scores]
            result.scores = {s["name"]: s["score"] for s in scores}
            result.risks = risks
            result.full_analysis = ai_content

        # Update session status and title
        if dec_session.title == "New Decision" and len(user_message) > 10:
            dec_session.title = user_message[:80]
        if scores:
            dec_session.status = "completed"

        db.session.commit()

        return jsonify(
            session_id=dec_session.id,
            domain=domain,
            message=ai_content,
            scores=scores,
            risks=risks[:6],
            has_analysis=bool(scores),
            tokens_used=ai_result.get("tokens_used", 0),
        )

    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Chat send error: %s", exc)
        return jsonify(error="Internal error. Please try again."), 500


@chat_bp.route("/sessions", methods=["GET"])
def list_sessions():
    """GET /api/chat/sessions — List all sessions for the current user."""
    token = session.get("user_token")
    if not token:
        return jsonify(sessions=[])

    sessions_data = (
        DecisionSession.query
        .filter_by(session_token=token)
        .order_by(DecisionSession.updated_at.desc())
        .limit(50)
        .all()
    )
    return jsonify(sessions=[s.to_dict() for s in sessions_data])


@chat_bp.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id: str):
    """GET /api/chat/sessions/<id> — Load full session with messages."""
    token = session.get("user_token")
    ds = DecisionSession.query.filter_by(id=session_id, session_token=token).first()
    if not ds:
        return jsonify(error="Session not found."), 404

    all_msgs = db.session.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == ds.id)
        .order_by(ChatMessage.created_at)
    ).scalars().all()
    messages = [m.to_dict() for m in all_msgs]
    result = ds.result.to_dict() if ds.result else None

    return jsonify(
        session=ds.to_dict(),
        messages=messages,
        result=result,
    )


@chat_bp.route("/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id: str):
    """DELETE /api/chat/sessions/<id>"""
    token = session.get("user_token")
    ds = DecisionSession.query.filter_by(id=session_id, session_token=token).first()
    if not ds:
        return jsonify(error="Session not found."), 404

    db.session.delete(ds)
    db.session.commit()
    return jsonify(message="Session deleted.")
