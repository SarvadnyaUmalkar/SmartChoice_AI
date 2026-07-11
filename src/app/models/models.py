"""
SmartChoice AI — SQLAlchemy Database Models
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _gen_uuid() -> str:
    return str(uuid.uuid4())


class DecisionSession(db.Model):
    """Represents a single decision-making conversation session."""
    __tablename__ = "decision_sessions"

    id = db.Column(db.String(36), primary_key=True, default=_gen_uuid)
    session_token = db.Column(db.String(64), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False, default="Untitled Decision")
    domain = db.Column(db.String(50), nullable=False, default="general")
    status = db.Column(db.String(20), nullable=False, default="active")
    # active | completed | archived
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    messages = db.relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan",
        order_by="ChatMessage.created_at", lazy="select"
    )
    result = db.relationship(
        "DecisionResult", back_populates="session", uselist=False, cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "domain": self.domain,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "message_count": len(self.messages),
        }


class ChatMessage(db.Model):
    """Individual message within a decision session."""
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String(36), db.ForeignKey("decision_sessions.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False)   # "user" | "assistant"
    content = db.Column(db.Text, nullable=False)
    tokens_used = db.Column(db.Integer, nullable=True, default=0)
    model_used = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    session = db.relationship("DecisionSession", back_populates="messages")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }


class DecisionResult(db.Model):
    """Stored analytical result for a completed decision session."""
    __tablename__ = "decision_results"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String(36), db.ForeignKey("decision_sessions.id"), nullable=False, unique=True)

    options_json = db.Column(db.Text, nullable=True)        # JSON list of option names
    scores_json = db.Column(db.Text, nullable=True)         # JSON {option: score}
    confidence_json = db.Column(db.Text, nullable=True)     # JSON {option: confidence}
    risks_json = db.Column(db.Text, nullable=True)          # JSON list of risk dicts
    matrix_json = db.Column(db.Text, nullable=True)         # JSON comparison matrix
    recommendation = db.Column(db.Text, nullable=True)      # Final recommendation text
    full_analysis = db.Column(db.Text, nullable=True)       # Complete AI response

    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    session = db.relationship("DecisionSession", back_populates="result")

    # ── JSON helpers ───────────────────────────────────────────────────────────
    @property
    def options(self) -> list:
        return json.loads(self.options_json) if self.options_json else []

    @options.setter
    def options(self, value: list) -> None:
        self.options_json = json.dumps(value)

    @property
    def scores(self) -> dict:
        return json.loads(self.scores_json) if self.scores_json else {}

    @scores.setter
    def scores(self, value: dict) -> None:
        self.scores_json = json.dumps(value)

    @property
    def confidence(self) -> dict:
        return json.loads(self.confidence_json) if self.confidence_json else {}

    @confidence.setter
    def confidence(self, value: dict) -> None:
        self.confidence_json = json.dumps(value)

    @property
    def risks(self) -> list:
        return json.loads(self.risks_json) if self.risks_json else []

    @risks.setter
    def risks(self, value: list) -> None:
        self.risks_json = json.dumps(value)

    @property
    def matrix(self) -> dict:
        return json.loads(self.matrix_json) if self.matrix_json else {}

    @matrix.setter
    def matrix(self, value: dict) -> None:
        self.matrix_json = json.dumps(value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "options": self.options,
            "scores": self.scores,
            "confidence": self.confidence,
            "risks": self.risks,
            "matrix": self.matrix,
            "recommendation": self.recommendation,
            "created_at": self.created_at.isoformat(),
        }
