from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from core.gemini_service import gemini_assistant
from core.notifications import notifier
from models import User, Hospital

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Landing and demo launcher page."""
    # Find sample mock patient and hospitals for quick demo links
    sample_patient = User.query.filter_by(role="patient").first()
    hospitals_count = Hospital.query.count()
    return render_template(
        "index.html",
        sample_patient=sample_patient,
        hospitals_count=hospitals_count
    )


@main_bp.route("/set-language/<lang>")
def set_language(lang):
    """Switch active session language ('en', 'hi', 'mr')."""
    if lang in ["en", "hi", "mr"]:
        session["lang"] = lang
    referrer = request.referrer or url_for("main.index")
    return redirect(referrer)


@main_bp.route("/api/doubt", methods=["POST"])
def ask_doubt():
    """API endpoint for Gemini Health Assistant."""
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"status": "error", "message": "Query cannot be empty"}), 400

    lang = session.get("lang", "en")
    result = gemini_assistant.answer_health_doubt(query=query, language=lang)
    return jsonify(result)


@main_bp.route("/api/simulated-sms", methods=["GET"])
def get_simulated_sms():
    """Fetch live simulated SMS log for judge demo drawer."""
    messages = notifier.get_recent_messages(limit=15)
    return jsonify({"status": "success", "messages": messages})


@main_bp.route("/api/quick-login/<role>/<app_id>")
def quick_demo_login(role, app_id):
    """Convenience helper for judges/evaluators to switch personas instantly."""
    user = User.query.filter_by(app_id=app_id).first()
    if user:
        session["user_id"] = user.id
        session["user_role"] = user.role
        session["user_name"] = user.full_name
        session["app_id"] = user.app_id
        if user.role in ["doctor", "admin"]:
            return redirect(url_for("portal.dashboard"))
        return redirect(url_for("app_routes.index"))
    return redirect(url_for("main.index"))
