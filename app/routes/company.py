from flask import Blueprint, jsonify, current_app

company_bp = Blueprint('company', __name__)

@company_bp.route('/companies', methods=['GET'])
def get_companies():
    supabase = current_app.supabase
    response = supabase.table('companies').select('*').execute()
    companies = response.data
    return jsonify(companies)