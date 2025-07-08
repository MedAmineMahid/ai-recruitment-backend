import json
from flask import Blueprint, jsonify, current_app, request
from app.services.job_services import create_job, get_jobs_data, get_job_by_id, get_recommended_jobs, get_candidates_for_job
from app.services.application_service import create_application
from app.utils.auth_utils import verify_supabase_token


job_bp = Blueprint("job", __name__)


@job_bp.route("", methods=["POST"])
def post_job():
    try:
        job_data = request.json
        if not job_data:
            return jsonify({'error': 'No job data provided'}), 400

        # Assuming create_job handles company_id internally or it's passed in job_data
        new_job = create_job(job_data)
        return jsonify(new_job), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error in post_job: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@job_bp.route('/jobs/<int:job_id>/apply', methods=['POST'])
def apply_to_job(job_id):
    try:
        # The create_application service handles request parsing and validation internally
        response, status = create_application()
        return jsonify(response), status
    except Exception as e:
        current_app.logger.error(f"Error applying to job {job_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@job_bp.route("", methods=["GET", "OPTIONS"])

def get_jobs():
    try:
        # Parse query parameters
        search = request.args.get("search")
        location = request.args.get("location")
        contract_type = request.args.get("contract_type")
        work_mode = request.args.getlist("work_mode")
        min_salary = request.args.get("min_salary", type=float)
        page = request.args.get("page", default=1, type=int)
        limit = request.args.get("limit", default=20, type=int)
        
        # Prepare filters dict
        filters = {
            "search": search,
            "location": location,
            "contract_type": contract_type,
            "work_mode": work_mode,
            "min_salary": min_salary,
            "page": page,
            "limit": limit
        }
        
        jobs = get_jobs_data(filters)
        return jsonify({"jobs": jobs}), 200
    except Exception as e:
        current_app.logger.error(f"Error getting jobs: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@job_bp.route("/<job_id>", methods=["GET", "OPTIONS"])
def get_job(job_id):
    if request.method == "OPTIONS":
        return jsonify({}), 200
    try:
        job = get_job_by_id(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        return jsonify(job), 200
    except Exception as e:
        current_app.logger.error(f"Error getting job {job_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@job_bp.route("/recommended", methods=["GET", "OPTIONS"])
def get_recommended():
    try:
        jobs = get_recommended_jobs()
        return jsonify({"jobs": jobs}), 200
    except Exception as e:
        current_app.logger.error(f"Error getting recommended jobs: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@job_bp.route('/<job_id>/candidates', methods=['GET', 'OPTIONS'])
def get_job_candidates(job_id):
    try:
        # Placeholder for authentication/authorization
        # Ensure only recruiters associated with the job's company can access this

        candidates = get_candidates_for_job(job_id)
        return jsonify(candidates), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching candidates for job {job_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
    
    
    