from flask import Blueprint, jsonify, request
from app.services.dashboard_services import get_recruiter_dashboard_data
from app.utils.auth_utils import is_recruiter, get_current_user_id

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/recruiter/<uuid:recruiter_id>', methods=['GET'])
def recruiter_dashboard(recruiter_id):
    try:
        current_user_id = get_current_user_id()
        if not current_user_id or not is_recruiter(current_user_id):
            return jsonify({'error': 'Unauthorized: You must be logged in as a recruiter to view this dashboard.'}), 403

        if str(recruiter_id) != current_user_id:
            return jsonify({'error': 'Unauthorized: You can only view your own dashboard.'}), 403

        data = get_recruiter_dashboard_data(str(recruiter_id))
        return jsonify(data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500