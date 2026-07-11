"""
SmartChoice AI — History Blueprint
"""
from __future__ import annotations

from flask import Blueprint, jsonify, session

from app.models import DecisionSession

history_bp = Blueprint("history", __name__)


@history_bp.route("/", methods=["GET"])
def get_history():
    """GET /api/history/ — Return decision history timeline for current user."""
    token = session.get("user_token")
    if not token:
        return jsonify(history=[])

    sessions = (
        DecisionSession.query
        .filter_by(session_token=token)
        .order_by(DecisionSession.updated_at.desc())
        .limit(100)
        .all()
    )

    history = []
    for s in sessions:
        item = s.to_dict()
        if s.result:
            item["scores"] = s.result.scores
            item["top_recommendation"] = s.result.recommendation
        history.append(item)

    return jsonify(history=history)


@history_bp.route("/stats", methods=["GET"])
def get_stats():
    """GET /api/history/stats — Summary statistics for the dashboard."""
    token = session.get("user_token")
    if not token:
        return jsonify(stats={})

    sessions = DecisionSession.query.filter_by(session_token=token).all()
    total = len(sessions)
    completed = sum(1 for s in sessions if s.status == "completed")
    domains: dict[str, int] = {}
    for s in sessions:
        domains[s.domain] = domains.get(s.domain, 0) + 1

    return jsonify(
        stats={
            "total_decisions": total,
            "completed": completed,
            "active": total - completed,
            "domains_breakdown": domains,
        }
    )
