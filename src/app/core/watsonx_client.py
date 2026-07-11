"""
SmartChoice AI — IBM Watsonx.ai Granite Client
Connects to IBM Cloud PUBLIC SaaS (Sydney region: au-syd.ml.cloud.ibm.com)
Uses ibm-watsonx-ai==1.1.2 correct pattern for public cloud with api_key.
"""
from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from flask import current_app

from app.core.agent_instructions import MODEL_PARAMS, build_system_prompt

logger = logging.getLogger(__name__)

# ── Load .env before anything else ────────────────────────────────────────────
_ENV_PATH = Path(__file__).parent.parent.parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH, override=True)

# ── Cached client (per process) ───────────────────────────────────────────────
_watsonx_client = None
_cached_url     = None


# ─────────────────────────────────────────────────────────────────────────────
# Credential readers — always pull from os.environ FIRST so .env changes
# (after a restart) are always picked up, not stale class-level values.
# ─────────────────────────────────────────────────────────────────────────────

def _env(key: str, default: str = "") -> str:
    """Read from os.environ first, then Flask config, then default."""
    val = os.environ.get(key, "").strip()
    if val:
        return val
    try:
        val = (current_app.config.get(key) or "").strip()
    except RuntimeError:
        pass
    return val or default


def _url()        -> str: return _env("IBM_WATSONX_URL", "https://au-syd.ml.cloud.ibm.com")
def _api_key()    -> str: return _env("IBM_API_KEY")
def _project_id() -> str: return _env("IBM_PROJECT_ID")
def _model_id()   -> str: return _env("GRANITE_MODEL_ID", "ibm/granite-13b-instruct-v2")


# ─────────────────────────────────────────────────────────────────────────────
# Client factory
# The ONLY correct pattern for ibm-watsonx-ai SDK on IBM Cloud PUBLIC SaaS is:
#
#   from ibm_watsonx_ai import Credentials, APIClient
#   creds  = Credentials(url=<region_url>, api_key=<iam_api_key>)
#   client = APIClient(creds)
#
# DO NOT pass: username, password, version, token — those are Cloud Pak for
# Data (on-premise) fields and will produce the "Missing version for CPD" error.
# ─────────────────────────────────────────────────────────────────────────────

def _get_client():
    global _watsonx_client, _cached_url

    region_url = _url()
    api_key    = _api_key()

    if not api_key:
        raise ValueError("IBM_API_KEY is blank. Set it in .env and restart Flask.")

    # Rebuild if URL changed or cache is empty
    if _watsonx_client is not None and _cached_url == region_url:
        return _watsonx_client

    from ibm_watsonx_ai import APIClient, Credentials

    logger.info("Creating IBM Watsonx APIClient → %s", region_url)

    # ── IBM Cloud PUBLIC SaaS constructor ─────────────────────────────────────
    # api_key  → SDK exchanges it for an IAM bearer token automatically.
    # url      → must be the regional endpoint (au-syd, us-south, eu-de, etc.)
    # No version, no username, no password — those are CPD on-prem fields.
    creds = Credentials(url=region_url, api_key=api_key)

    _watsonx_client = APIClient(creds)
    _cached_url     = region_url

    logger.info("IBM Watsonx APIClient ready → %s", region_url)
    return _watsonx_client


# ─────────────────────────────────────────────────────────────────────────────
# Inference params — only keys the SDK accepts (no stop_sequences etc.)
# ─────────────────────────────────────────────────────────────────────────────

def _sdk_params() -> dict:
    return {
        "max_new_tokens":     int(MODEL_PARAMS.get("max_new_tokens", 2048)),
        "temperature":        float(MODEL_PARAMS.get("temperature", 0.3)),
        "top_p":              float(MODEL_PARAMS.get("top_p", 0.85)),
        "top_k":              int(MODEL_PARAMS.get("top_k", 50)),
        "repetition_penalty": float(MODEL_PARAMS.get("repetition_penalty", 1.1)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main public function
# ─────────────────────────────────────────────────────────────────────────────

def generate_response(
    user_message: str,
    conversation_history: list[dict],
    domain: str | None = None,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Send prompt to IBM Granite, return structured response dict."""

    api_key    = _api_key()
    project_id = _project_id()
    model      = _model_id()
    region_url = _url()

    # Pre-flight checks — return in-chat error immediately, never crash Flask
    if not api_key:
        return _fallback("IBM_API_KEY is blank in .env — add your IBM Cloud API key and restart Flask.")
    if not project_id:
        return _fallback("IBM_PROJECT_ID is blank in .env — add your Watsonx project ID and restart Flask.")

    logger.info("Calling Granite → url=%s  project=%s  model=%s", region_url, project_id, model)

    system_prompt = build_system_prompt(domain)
    prompt        = _build_prompt(system_prompt, conversation_history, user_message)
    params        = _sdk_params()

    for attempt in range(1, max_retries + 1):
        try:
            client = _get_client()

            from ibm_watsonx_ai.foundation_models import ModelInference

            inference = ModelInference(
                model_id=model,
                api_client=client,
                project_id=project_id,
                params=params,
            )

            raw     = inference.generate_text(prompt=prompt)
            content = (raw if isinstance(raw, str) else str(raw)).strip()

            logger.info("✅ Granite success → url=%s  len=%d", region_url, len(content))

            return {
                "content":        content,
                "tokens_used":    len(prompt.split()) + len(content.split()),
                "model":          model,
                "domain":         domain or _detect_domain(user_message),
                "has_scores":     bool(re.search(r"\d+\s*/\s*100|decision score", content, re.I)),
                "has_comparison": bool(re.search(r"option [a-z]|vs\.|versus", content, re.I)),
            }

        except Exception as exc:
            err = str(exc)
            logger.warning("Attempt %d/%d failed: %s", attempt, max_retries, err)

            # container_not_found = wrong region or wrong project ID — don't retry
            if "container_not_found" in err.lower() or "404" in err:
                return _fallback(
                    f"Project not found at {region_url}. "
                    f"Confirm IBM_PROJECT_ID={project_id} exists in the Sydney (au-syd) region "
                    f"at dataplatform.cloud.ibm.com."
                )

            if attempt < max_retries:
                time.sleep(2)

    return _fallback(f"All {max_retries} attempts failed. Last error: {err}")


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_prompt(system: str, history: list[dict], user_msg: str) -> str:
    lines = [f"<|system|>\n{system}\n<|end|>"]
    for turn in history[-6:]:
        tag = "<|user|>" if turn.get("role") == "user" else "<|assistant|>"
        lines.append(f"{tag}\n{turn.get('content', '')}\n<|end|>")
    lines.append(f"<|user|>\n{user_msg}\n<|end|>")
    lines.append("<|assistant|>")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Domain detector
# ─────────────────────────────────────────────────────────────────────────────

def _detect_domain(text: str) -> str:
    tl = text.lower()
    checks = {
        "education":  ["mba", "ms ", "degree", "college", "university", "course"],
        "career":     ["job", "career", "switch", "promotion", "salary"],
        "investment": ["sip", "mutual fund", "fd", "fixed deposit", "stocks", "portfolio"],
        "technology": ["laptop", "phone", "smartphone", "software", "server"],
        "banking":    ["credit card", "loan", "emi", "interest rate", "bank"],
        "insurance":  ["insurance", "policy", "coverage", "term", "premium"],
        "business":   ["build vs buy", "vendor", "startup", "enterprise"],
        "daily_life": ["buy", "purchase", "choose", "pick", "decide"],
    }
    for dom, kws in checks.items():
        if any(kw in tl for kw in kws):
            return dom
    return "general"


# ─────────────────────────────────────────────────────────────────────────────
# Fallback — never crashes Flask, always returns a valid response dict
# ─────────────────────────────────────────────────────────────────────────────

def _fallback(error: str, domain: str | None = None) -> dict[str, Any]:
    logger.error("IBM Watsonx error: %s", error)
    content = (
        "## ⚠️ Cannot Connect to IBM Watsonx.ai\n\n"
        f"**Error:** {error}\n\n"
        "**Your `.env` must have exactly these values:**\n\n"
        "```\n"
        "IBM_API_KEY=<your IBM Cloud API key>\n"
        "IBM_PROJECT_ID=3e104f66-a1f0-4796-9526-37c355cad5c8\n"
        "IBM_WATSONX_URL=https://au-syd.ml.cloud.ibm.com\n"
        "GRANITE_MODEL_ID=ibm/granite-13b-instruct-v2\n"
        "```\n\n"
        "After editing `.env` → stop Flask (Ctrl+C) → run `python run.py` again."
    )
    return {
        "content": content, "tokens_used": 0, "model": "unavailable",
        "domain": domain or "general", "has_scores": False,
        "has_comparison": False, "error": error,
    }
