"""Main blueprint — serves frontend pages."""
from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


from flask import jsonify
import os


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@main_bp.route("/history")
def history_page():
    return render_template("history.html")


@main_bp.route("/api/health")
def health():
    """Simple health-check endpoint — returns server status and credential state."""
    api_key_set    = bool(os.environ.get("IBM_API_KEY", "").strip())
    project_id_set = bool(os.environ.get("IBM_PROJECT_ID", "").strip())
    return jsonify(
        status="ok",
        server="SmartChoice AI",
        ibm_api_key_set=api_key_set,
        ibm_project_id_set=project_id_set,
        ready=api_key_set and project_id_set,
    )
