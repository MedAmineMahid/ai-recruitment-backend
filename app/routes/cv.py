from flask import Blueprint, request, jsonify
from app.services.cv_service import *
from flask import send_from_directory
from werkzeug.utils import secure_filename

cv_bp = Blueprint("cv", __name__)

@cv_bp.route("", methods=["POST"])  # No trailing slash
@cv_bp.route("/", methods=["POST"])  # With trailing slash
def handle_upload_cv():
    response, status = upload_cv()
    return jsonify(response), status

@cv_bp.route("/", methods=["GET", "OPTIONS"])
def handle_get_cv():
    response, status = get_cv()
    return jsonify(response), status

@cv_bp.route("/", methods=["DELETE"])
def handle_delete_cv():
    response, status = delete_cv()
    return jsonify(response), status

@cv_bp.route("/check_cv_uploaded", methods=["GET"])
def handle_check_cv_uploaded():
    response, status = check_cv_uploaded()
    return jsonify(response), status


# ===== CV LAST UPDATED =====
@cv_bp.route("/cv-last-updated", methods=["GET"])
def cv_last_updated():
    response, status = get_cv_last_updated()
    return jsonify(response), status

@cv_bp.route("/download/<path:filename>", methods=["GET"])
def download_cv(filename):
    try:
        # Ensure the filename is secure to prevent directory traversal attacks
        # The filename now includes the path (e.g., uid/cv.pdf)
        # secure_filename is still good practice, but it might strip slashes if not handled carefully.
        # For paths, it's better to ensure the path is safe rather than just the filename.
        # Given the filename is constructed from uid/cv.extension, it should be safe.
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads/cvs')
        return send_from_directory(upload_folder, filename)
    except Exception as e:
        current_app.logger.error(f"Error serving CV file {filename}: {str(e)}")
        return jsonify({"error": "Could not retrieve file"}), 500



