from flask import request, current_app
from supabase import Client
from flask import request, current_app

def verify_supabase_token() -> str | None:
    auth_header = request.headers.get('Authorization')

    if not auth_header:
        current_app.logger.warning("Authorization header missing.")
        return None
    if not auth_header.startswith('Bearer '):
        current_app.logger.warning(f"Authorization header malformed: {auth_header}")
        return None

    token = auth_header.split(' ')[1]
    current_app.logger.info(f"Extracted Token: {token}")
    supabase: Client = current_app.supabase

    try:
        user = supabase.auth.get_user(token)
        current_app.logger.info(f"Supabase token verified for user: {user.user.id}")
        return user.user.id
    except Exception as e:
        current_app.logger.error(f"Supabase token verification failed: {str(e)}")
        return None

def get_current_user_id():
    # In a real application, this would extract the user ID from the request context (e.g., from a JWT token)
    # For now, we'll use the verified Supabase token.
    return verify_supabase_token()

def is_recruiter(user_id):
    supabase: Client = current_app.supabase
    try:
        response = supabase.table('recruiters').select('id').eq('id', user_id).single().execute()
        return response.data is not None
    except Exception as e:
        current_app.logger.error(f"Error checking if user {user_id} is recruiter: {str(e)}")
        return False

def get_user_role(user_id):
    # Placeholder for getting the user's role
    # In a real application, this would involve fetching the user's role from a database or authentication service
    return "applicant"  # Default to 'applicant' for now for testing purposes