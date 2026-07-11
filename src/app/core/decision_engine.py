"""
SmartChoice AI — Decision Scoring & Analysis Engine
Provides mathematical scoring, SWOT extraction, and comparison matrix generation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.core.agent_instructions import (
    CONFIDENCE_PENALTY_PER_GAP,
    DEFAULT_CRITERIA_WEIGHTS,
    DOMAIN_CRITERIA_WEIGHTS,
    MIN_CONFIDENCE_SCORE,
    SCORE_SCALE,
)


@dataclass
class OptionScore:
    name: str
    domain: str
    criteria_scores: dict[str, float] = field(default_factory=dict)
    decision_score: float = 0.0
    confidence_score: float = 0.0
    risk_level: str = "MEDIUM"
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    threats: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "domain": self.domain,
            "criteria_scores": self.criteria_scores,
            "decision_score": round(self.decision_score, 1),
            "confidence_score": round(self.confidence_score, 1),
            "risk_level": self.risk_level,
            "pros": self.pros,
            "cons": self.cons,
            "opportunities": self.opportunities,
            "threats": self.threats,
        }


def score_options(
    options: list[str],
    raw_criteria: dict[str, dict[str, float]],
    domain: str | None = None,
    missing_data_count: int = 0,
) -> list[OptionScore]:
    """
    Compute Decision Score and Confidence Score for each option.

    Args:
        options: List of option names (e.g., ["MBA", "MS in Data Science"])
        raw_criteria: {option_name: {criterion: raw_score_0_to_10}}
        domain: Decision domain for weight selection
        missing_data_count: Number of missing data points (affects confidence)
    """
    weights = DOMAIN_CRITERIA_WEIGHTS.get(domain or "", DEFAULT_CRITERIA_WEIGHTS)
    confidence = max(
        MIN_CONFIDENCE_SCORE,
        100 - (missing_data_count * CONFIDENCE_PENALTY_PER_GAP),
    )

    scored = []
    for option in options:
        crits = raw_criteria.get(option, {})
        weighted_sum = sum(
            crits.get(crit, 5.0) * weight
            for crit, weight in weights.items()
        )
        decision_score = (weighted_sum / 10.0) * SCORE_SCALE

        scored.append(
            OptionScore(
                name=option,
                domain=domain or "general",
                criteria_scores=crits,
                decision_score=decision_score,
                confidence_score=confidence,
            )
        )

    return scored


def parse_scores_from_response(response_text: str) -> list[dict[str, Any]]:
    """
    Extract structured scores from Granite's markdown response.
    Looks for patterns like "Option X: 78/100" or "Decision Score: 82".
    """
    scores = []
    patterns = [
        r"(?P<name>[A-Za-z][^:\n]+?):\s*(?P<score>\d{1,3})\s*/\s*100",
        r"(?P<name>[A-Za-z][^:\n]+?)\s*[-–—]\s*(?:Decision\s*)?Score[:\s]+(?P<score>\d{1,3})",
        r"\*\*(?P<name>[^*]+)\*\*[^0-9]*(?P<score>\d{1,3})\s*/\s*100",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, response_text, re.IGNORECASE):
            name = match.group("name").strip()
            raw_score = int(match.group("score"))
            if 0 <= raw_score <= 100 and len(name) < 80:
                scores.append({"name": name, "score": raw_score})

    # De-duplicate by name
    seen = set()
    unique = []
    for s in scores:
        key = s["name"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


def parse_risks_from_response(response_text: str) -> list[dict[str, Any]]:
    """
    Extract risk items from the AI response text.
    Returns a list of {item, severity, probability, impact, mitigation}.
    """
    risks = []
    risk_section = re.search(
        r"risk[^#]*?(?=##|\Z)", response_text, re.IGNORECASE | re.DOTALL
    )
    if not risk_section:
        return risks

    block = risk_section.group(0)
    # Look for HIGH / MEDIUM / LOW labels
    for line in block.splitlines():
        line = line.strip("-• *\t")
        if not line:
            continue
        severity = "MEDIUM"
        if re.search(r"\bHIGH\b", line, re.I):
            severity = "HIGH"
        elif re.search(r"\bLOW\b", line, re.I):
            severity = "LOW"

        # Strip severity labels from item text
        item_text = re.sub(r"\b(HIGH|MEDIUM|LOW)\b", "", line, flags=re.I).strip(" :-|")
        if item_text and len(item_text) > 5:
            risks.append({"item": item_text[:160], "severity": severity})

    return risks[:12]  # cap at 12 risk items


def build_comparison_matrix(
    options: list[str],
    criteria: list[str],
    raw_criteria: dict[str, dict[str, float]],
) -> dict[str, Any]:
    """
    Build a normalized comparison matrix ready for frontend rendering.

    Returns:
        {
            "options": [...],
            "criteria": [...],
            "matrix": {option: {criterion: {"raw": float, "normalized": float, "winner": bool}}}
            "winner_per_criterion": {criterion: option_name}
        }
    """
    matrix: dict[str, dict] = {opt: {} for opt in options}
    winner_per_criterion: dict[str, str] = {}

    for criterion in criteria:
        scores = {opt: raw_criteria.get(opt, {}).get(criterion, 5.0) for opt in options}
        max_score = max(scores.values()) or 1
        winner = max(scores, key=scores.__getitem__)
        winner_per_criterion[criterion] = winner

        for opt in options:
            raw = scores[opt]
            normalized = (raw / 10.0) * 100
            matrix[opt][criterion] = {
                "raw": round(raw, 1),
                "normalized": round(normalized, 1),
                "winner": opt == winner,
            }

    return {
        "options": options,
        "criteria": criteria,
        "matrix": matrix,
        "winner_per_criterion": winner_per_criterion,
    }


def detect_domain_from_text(text: str) -> str:
    """Detect the most likely decision domain from free text."""
    text_lower = text.lower()
    domain_keywords = {
        "education":  ["mba", "ms ", "degree", "college", "university", "course", "admission"],
        "career":     ["job", "career", "switch", "promotion", "offer letter", "salary"],
        "investment": ["sip", "mutual fund", "fd", "fixed deposit", "stocks", "returns", "portfolio"],
        "technology": ["laptop", "phone", "smartphone", "software", "server", "cloud"],
        "banking":    ["credit card", "loan", "emi", "interest rate", "bank account"],
        "insurance":  ["insurance", "policy", "coverage", "term", "premium"],
        "business":   ["build vs buy", "vendor", "startup", "enterprise", "strategy"],
    }
    for domain, keywords in domain_keywords.items():
        if any(kw in text_lower for kw in keywords):
            return domain
    return "daily_life"
