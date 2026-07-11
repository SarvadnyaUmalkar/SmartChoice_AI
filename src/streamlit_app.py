"""SmartChoice AI — Application Entry Point"""
import os
from pathlib import Path

# ── Safe Environment Loading (Prevents crashing on Hugging Face) ──────────
try:
    from dotenv import load_dotenv
    _ENV_PATH = Path(__file__).parent / ".env"
    _loaded = load_dotenv(dotenv_path=_ENV_PATH, override=True)
except ImportError:
    # Hugging Face loads your Settings Secrets automatically, so we can skip dotenv!
    _loaded = False
    _ENV_PATH = "Hugging Face Repository Secrets"

# ── Startup diagnostic — printed to terminal on every launch ──────────────────
print("\n" + "─" * 60)
print("  SmartChoice AI — Startup Diagnostics")
print("─" * 60)
print(f"  .env file found   : {'✅ YES — ' + str(_ENV_PATH) if _loaded else 'ℹ️  Using Hugging Face Saved Secrets Keys'}")

_api_key     = os.environ.get("IBM_API_KEY", "")
_project_id  = os.environ.get("IBM_PROJECT_ID", "")
_secret_key  = os.environ.get("SECRET_KEY", "")
_watsonx_url = os.environ.get("IBM_WATSONX_URL", "")   # empty = not set in .env
_model_id    = os.environ.get("GRANITE_MODEL_ID", "ibm/granite-13b-instruct-v2")

print(f"  IBM_API_KEY       : {'✅ SET  (' + '*' * min(8, len(_api_key)) + '...)' if _api_key else '❌ MISSING — add to Settings Secrets'}")
print(f"  IBM_PROJECT_ID    : {'✅ SET  (' + _project_id[:8] + '...)' if _project_id else '❌ MISSING — add to Settings Secrets'}")
_url_display = _watsonx_url if _watsonx_url else "❌ MISSING — add IBM_WATSONX_URL=https://au-syd.ml.cloud.ibm.com"
print(f"  IBM_WATSONX_URL   : {_url_display}")
print(f"  GRANITE_MODEL_ID  : {_model_id}")
print(f"  SECRET_KEY        : {'✅ SET' if _secret_key and _secret_key != 'dev-secret-change-me' else '⚠️  Using default (change for production)'}")

if not _api_key or not _project_id:
    print("\n  ⚠️  IBM credentials missing. AI chat will show error messages.")
    print("  📝 Go to Space Settings -> Variables and secrets to add them.")
else:
    print("\n  ✅ All IBM credentials set. AI chat is ready.")
print("─" * 60 + "\n")

from app import create_app

env = os.environ.get("FLASK_ENV", "development")
config_map = {
    "development": "app.config.DevelopmentConfig",
    "production":  "app.config.ProductionConfig",
    "testing":     "app.config.TestingConfig",
}

app = create_app(config_map.get(env, "app.config.DevelopmentConfig"))

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8501)),
        debug=app.config.get("DEBUG", False),
    )
