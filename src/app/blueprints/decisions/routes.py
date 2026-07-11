"""
SmartChoice AI — Decisions Blueprint
Handles structured multi-option comparison and scoring endpoints.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request, session, current_app

from app import db, limiter
from app.models import DecisionSession, DecisionResult
from app.core.watsonx_client import generate_response
from app.core.decision_engine import (
    build_comparison_matrix,
    detect_domain_from_text,
    parse_risks_from_response,
    parse_scores_from_response,
)
from app.core.agent_instructions import SUPPORTED_DOMAINS, DEFAULT_CRITERIA_WEIGHTS

decisions_bp = Blueprint("decisions", __name__)


@decisions_bp.route("/compare", methods=["POST"])
@limiter.limit("20 per minute")
def compare_options():
    """
    POST /api/decisions/compare
    Body: {
        "session_id": str,
        "options": ["Option A", "Option B", ...],
        "criteria": ["cost", "performance", ...],  # optional overrides
        "context": str,  # additional free-text context
        "domain": str | null
    }
    """
    data = request.get_json(silent=True) or {}
    options = data.get("options", [])
    context = (data.get("context") or "").strip()
    domain = data.get("domain") or detect_domain_from_text(context)
    session_id = data.get("session_id")

    if not options or len(options) < 2:
        return jsonify(error="At least 2 options are required."), 400
    if len(options) > 5:
        return jsonify(error="Maximum 5 options allowed per comparison."), 400

    criteria = data.get("criteria") or list(DEFAULT_CRITERIA_WEIGHTS.keys())

    prompt = _build_comparison_prompt(options, context, domain, criteria)

    try:
        token = session.get("user_token")
        ds = None
        if session_id and token:
            ds = DecisionSession.query.filter_by(id=session_id, session_token=token).first()

        ai_result = generate_response(
            user_message=prompt,
            conversation_history=[],
            domain=domain,
        )
        content = ai_result["content"]

        scores = parse_scores_from_response(content)
        risks = parse_risks_from_response(content)

        # Build a synthetic raw_criteria dict from scores for matrix
        raw_criteria: dict[str, dict] = {
            opt: {c: scores[i]["score"] / 10.0 if i < len(scores) else 5.0
                  for c in criteria}
            for i, opt in enumerate(options)
        }

        # Refine using per-criterion score extraction if possible
        for sc in scores:
            for opt in options:
                if sc["name"].lower() in opt.lower() or opt.lower() in sc["name"].lower():
                    for crit in criteria:
                        raw_criteria[opt][crit] = sc["score"] / 10.0
                    break

        matrix = build_comparison_matrix(options, criteria, raw_criteria)

        if ds:
            result = ds.result or DecisionResult(session_id=ds.id)
            result.options = options
            result.scores = {s["name"]: s["score"] for s in scores}
            result.risks = risks
            result.matrix = matrix
            result.full_analysis = content
            if not ds.result:
                db.session.add(result)
            ds.status = "completed"
            db.session.commit()

        return jsonify(
            analysis=content,
            scores=scores,
            risks=risks,
            matrix=matrix,
            domain=domain,
        )

    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Compare error: %s", exc)
        return jsonify(error="Comparison failed. Please try again."), 500


@decisions_bp.route("/domains", methods=["GET"])
def get_domains():
    """GET /api/decisions/domains — Return all supported decision domains."""
    return jsonify(
        domains=[
            {"id": k, "label": k.replace("_", " ").title(), "description": v}
            for k, v in SUPPORTED_DOMAINS.items()
        ]
    )


@decisions_bp.route("/templates", methods=["GET"])
def get_templates():
    """GET /api/decisions/templates — Return built-in decision templates."""
    import json
    import os
    template_path = os.path.abspath(
        os.path.join(current_app.root_path, "..", "data", "templates", "decision_templates.json")
    )
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            templates = json.load(f)
        return jsonify(templates=templates)
    except FileNotFoundError:
        current_app.logger.warning("Template file not found: %s", template_path)
        return jsonify(templates=[])


def _build_comparison_prompt(
    options: list[str],
    context: str,
    domain: str,
    criteria: list[str],
) -> str:
    option_list = "\n".join(f"  - {o}" for o in options)
    criteria_list = ", ".join(criteria)
    return (
        f"Perform a comprehensive multi-option decision analysis for the following:\n\n"
        f"**DECISION CONTEXT:** {context or 'No additional context provided.'}\n"
        f"**DOMAIN:** {domain}\n\n"
        f"**OPTIONS TO COMPARE:**\n{option_list}\n\n"
        f"**EVALUATION CRITERIA:** {criteria_list}\n\n"
        f"For each option: apply all active reasoning frameworks, calculate a Decision Score "
        f"(0–100) and Confidence Score (%), generate a complete comparison matrix, "
        f"identify risks, and provide a clear final recommendation with contingency paths.\n"
        f"Format scores exactly as: 'Option Name: XX/100'"
    )
