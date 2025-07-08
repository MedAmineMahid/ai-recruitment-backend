from flask import current_app

def get_db_connection():
    # Return the Supabase client directly
    return current_app.supabase