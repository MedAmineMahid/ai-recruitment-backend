from flask import Blueprint, request, jsonify
from flask import Blueprint, jsonify, request
from app.services.profile_service import get_profile_data, update_profile_data, get_experiences, add_experience, update_experience, delete_experience, get_languages, update_languages, get_certifications, update_certifications, get_job_preferences, update_job_preferences

profile_bp = Blueprint("profile", __name__)

@profile_bp.route("", methods=["GET"])
@profile_bp.route("/<string:candidate_id>", methods=["GET"])
def get_profile(candidate_id=None):
    response, status = get_profile_data(candidate_id)
    return jsonify(response), status



@profile_bp.route("", methods=["PUT"])
def update_profile():
    response, status =  update_profile_data()
    return jsonify(response), status




@profile_bp.route("/experience", methods=["GET", "POST", "PUT", "DELETE"])
def experience(): 
    if request.method == "GET":
        response, status = get_experiences()
    elif request.method == "POST":
        response, status = add_experience()
    elif request.method == "PUT":
        response, status = update_experience()
    elif request.method == "DELETE":
        response, status = delete_experience()
    return jsonify(response), status

# @profile_bp.route("/education", methods=["GET", "POST", "PUT", "DELETE"])
# def education():
#     if request.method == "GET":
#         response, status = get_education()
#     elif request.method == "POST":
#         response, status = add_education()
#     elif request.method == "PUT":
#         response, status = update_education()
#     elif request.method == "DELETE":
#         response, status = delete_education()
#     return jsonify(response), status

# @profile_bp.route("/skills", methods=["GET", "PUT"])
# def skills():
#     if request.method == "GET":
#         response, status = get_skills()
#     elif request.method == "PUT":
#         response, status = update_skills()
#     return jsonify(response), status


# ===== LANGUAGES =====
@profile_bp.route("/languages", methods=["GET", "PUT"])
def languages():
    if request.method == "GET":
        response, status = get_languages()
    elif request.method == "PUT":
        data = request.get_json()
        response, status = update_languages(data.get("languages", []))
    return jsonify(response), status

# ===== CERTIFICATIONS =====
@profile_bp.route("/certifications", methods=["GET", "PUT"])
def certifications():
    if request.method == "GET":
        response, status = get_certifications()
    elif request.method == "PUT":
        data = request.get_json()
        response, status = update_certifications(data.get("certifications", []))
    return jsonify(response), status

# ===== JOB PREFERENCES =====
@profile_bp.route("/job-preferences", methods=["GET", "PUT"])
def job_preferences():
    if request.method == "GET":
        response, status = get_job_preferences()
    elif request.method == "PUT":
        data = request.get_json()
        response, status = update_job_preferences(data.get("job_preferences", {}))
    return jsonify(response), status

