from flask import current_app, request
from supabase import Client
import json
from datetime import datetime
from flask import current_app, request
from .cv_service import verify_supabase_token

def get_profile_data(candidate_id=None):
    if candidate_id:
        # If candidate_id is provided, bypass authentication and use it directly
        target_uid = candidate_id
    else:
        # If no candidate_id, authenticate the current user
        authenticated_uid = verify_supabase_token()
        if not authenticated_uid:
            return {"error": "Unauthorized"}, 401
        target_uid = authenticated_uid

    supabase: Client = current_app.supabase

    try:
        # Fetch candidate basic data
        current_app.logger.info(f"get_profile_data: Target UID: {target_uid}")

        # Fetch candidate basic data
        current_app.logger.info(f"get_profile_data: Fetching candidate data for UID: {target_uid}")
        candidate_response = supabase.table("candidates").select("*").eq("id", target_uid).single().execute()
        candidate_data = candidate_response.data or {}
        current_app.logger.info(f"get_profile_data: Raw candidate response: {candidate_response.data}")
        current_app.logger.info(f"get_profile_data: Processed candidate data: {candidate_data}")

        # Fetch candidate profile data
        current_app.logger.info(f"get_profile_data: Fetching profile data for UID: {target_uid}")
        profile_response = supabase.table("candidate_profiles").select("*").eq("candidate_id", target_uid).single().execute()
        profile_data = profile_response.data or {}
        current_app.logger.info(f"get_profile_data: Raw profile response: {profile_response.data}")
        current_app.logger.info(f"get_profile_data: Processed profile data: {profile_data}")

        # Combine into ProfileData structure
        profile = {
            "name": candidate_data.get("full_name", ""),
            "title": profile_data.get("title", ""),
            "location": profile_data.get("location", ""),
            "avatarUrl": profile_data.get("avatar_url", ""),
            "about": profile_data.get("about", ""),
            "experiences": json.loads(profile_data.get("experience") or "[]"),
            "education": json.loads(profile_data.get("education") or "[]"),
            "skills": {
                "extracted": {
                    "pySkills": profile_data.get("py_skills", []),
                    "skillnerSkills": profile_data.get("skillner_skills", [])
                },
                "added": profile_data.get("added_skills", [])
            },
            "languages": json.loads(profile_data.get("languages") or "[]"),
            "certifications": json.loads(profile_data.get("certifications") or "[]"),
            "jobPreferences": json.loads(profile_data.get("job_preferences") or "{}"),
            "contact": {
                "email": candidate_data.get("email", ""),
                "phone": candidate_data.get("phone", ""),
                "linkedin": profile_data.get("linkedin", ""),
                "website": profile_data.get("website", ""),
                "github": profile_data.get("github", "")
            },
            "cvLastUpdated": profile_data.get("updated_at", ""),
            "cvPdfUrl": candidate_data.get("cv_url", "")
        }

        return profile, 200

    except Exception as e:
        current_app.logger.error(f"Error getting profile data: {str(e)}")
        return {"error": "Internal server error"}, 500



def update_profile_data():
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    data = request.get_json()
    if not data:
        return {"error": "No data provided"}, 400
    
    current_app.logger.error(data)


    supabase: Client = current_app.supabase

    try:
        candidate_updates = {
            "full_name": data.get("name", ""),
            "phone": data.get("contact", {}).get("phone", ""),
        }

        profile_updates = {
            "location": data.get("location", ""),
            "title": data.get("title", ""),
            "about": data.get("about", ""),
            "experience": json.dumps(data.get("experiences", [])),
            "education": json.dumps(data.get("education", [])),
            "certifications": json.dumps(data.get("certifications", [])),
            "languages": json.dumps(data.get("languages", [])),
            "job_preferences": json.dumps(data.get("jobPreferences", {})),
            "py_skills": data.get("skills", {}).get("extracted", {}).get("pySkills", []),
            "skillner_skills": data.get("skills", {}).get("extracted", {}).get("skillnerSkills", []),
            "added_skills": data.get("skills", {}).get("added", []),
            "linkedin": data.get("contact", {}).get("linkedin", ""),
            "website": data.get("contact", {}).get("website", ""),
            "github": data.get("contact", {}).get("github", ""),
            "updated_at": datetime.now().isoformat()
        }

        supabase.table("candidates").update(candidate_updates).eq("id", authenticated_uid).execute()

        profile_exists = supabase.table("candidate_profiles").select("candidate_id").eq("candidate_id", authenticated_uid).execute()

        if profile_exists.data:
            supabase.table("candidate_profiles").update(profile_updates).eq("candidate_id", authenticated_uid).execute()
        else:
            profile_updates["candidate_id"] = authenticated_uid
            supabase.table("candidate_profiles").insert(profile_updates).execute()

        return {"success": True, "message": "Profile updated successfully"}, 200

    except Exception as e:
        current_app.logger.error(f"Error updating profile data: {str(e)}")
        return {"error": "Internal server error"}, 500


def get_experiences():
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    supabase: Client = current_app.supabase
    
    try:
        response = supabase.table("candidate_profiles").select("experience").eq("candidate_id", authenticated_uid).single().execute()
        experiences = json.loads(response.data.get("experience", "[]")) if response.data.get("experience") else []
        return {"experiences": experiences}, 200
    except Exception as e:
        current_app.logger.error(f"Error getting experiences: {str(e)}")
        return {"error": "Internal server error"}, 500

def add_experience():
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    new_experience = request.get_json()
    supabase: Client = current_app.supabase
    
    try:
        # Get current experiences
        response = supabase.table("candidate_profiles").select("experience").eq("candidate_id", authenticated_uid).single().execute()
        current_experiences = json.loads(response.data.get("experience", "[]")) if response.data.get("experience") else []
        
        # Add new experience
        current_experiences.append(new_experience)
        
        # Update database
        supabase.table("candidate_profiles").update({
            "experience": json.dumps(current_experiences),
            "updated_at": datetime.now().isoformat()
        }).eq("candidate_id", authenticated_uid).execute()
        
        return {"success": True}, 200
    except Exception as e:
        current_app.logger.error(f"Error adding experience: {str(e)}")
        return {"error": "Internal server error"}, 500

def update_experience():
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    data = request.get_json()
    experience_id = data.get("id")
    updated_experience = data.get("experience")
    
    if not experience_id or not updated_experience:
        return {"error": "Missing required fields"}, 400

    supabase: Client = current_app.supabase
    
    try:
        # Get current experiences
        response = supabase.table("candidate_profiles").select("experience").eq("candidate_id", authenticated_uid).single().execute()
        current_experiences = json.loads(response.data.get("experience", "[]")) if response.data.get("experience") else []
        
        # Find and update the experience
        updated = False
        for i, exp in enumerate(current_experiences):
            if exp.get("id") == experience_id:
                current_experiences[i] = updated_experience
                updated = True
                break
                
        if not updated:
            return {"error": "Experience not found"}, 404
            
        # Update database
        supabase.table("candidate_profiles").update({
            "experience": json.dumps(current_experiences),
            "updated_at": datetime.now().isoformat()
        }).eq("candidate_id", authenticated_uid).execute()
        
        return {"success": True}, 200
    except Exception as e:
        current_app.logger.error(f"Error updating experience: {str(e)}")
        return {"error": "Internal server error"}, 500

def delete_experience():
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    experience_id = request.args.get("id")
    if not experience_id:
        return {"error": "Missing experience ID"}, 400

    supabase: Client = current_app.supabase
    
    try:
        # Get current experiences
        response = supabase.table("candidate_profiles").select("experience").eq("candidate_id", authenticated_uid).single().execute()
        current_experiences = json.loads(response.data.get("experience", "[]")) if response.data.get("experience") else []
        
        # Remove the experience
        new_experiences = [exp for exp in current_experiences if exp.get("id") != experience_id]
        
        if len(new_experiences) == len(current_experiences):
            return {"error": "Experience not found"}, 404
            
        # Update database
        supabase.table("candidate_profiles").update({
            "experience": json.dumps(new_experiences),
            "updated_at": datetime.now().isoformat()
        }).eq("candidate_id", authenticated_uid).execute()
        
        return {"success": True}, 200
    except Exception as e:
        current_app.logger.error(f"Error deleting experience: {str(e)}")
        return {"error": "Internal server error"}, 500

# Similar functions for education (get_education, add_education, update_education, delete_education)
# Similar function for skills (get_skills, update_skills)


# ===== LANGUAGES =====
def get_languages():
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    supabase: Client = current_app.supabase
    
    try:
        response = supabase.table("candidate_profiles").select("languages").eq("candidate_id", authenticated_uid).single().execute()
        languages = json.loads(response.data.get("languages", "[]")) if response.data.get("languages") else []
        return {"languages": languages}, 200
    except Exception as e:
        current_app.logger.error(f"Error getting languages: {str(e)}")
        return {"error": "Internal server error"}, 500

def update_languages(languages_data):
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    supabase: Client = current_app.supabase
    
    try:
        supabase.table("candidate_profiles").update({
            "languages": json.dumps(languages_data),
            "updated_at": datetime.now().isoformat()
        }).eq("candidate_id", authenticated_uid).execute()
        return {"success": True}, 200
    except Exception as e:
        current_app.logger.error(f"Error updating languages: {str(e)}")
        return {"error": "Internal server error"}, 500

# ===== CERTIFICATIONS =====
def get_certifications():
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    supabase: Client = current_app.supabase
    
    try:
        response = supabase.table("candidate_profiles").select("certifications").eq("candidate_id", authenticated_uid).single().execute()
        certifications = json.loads(response.data.get("certifications", "[]")) if response.data.get("certifications") else []
        return {"certifications": certifications}, 200
    except Exception as e:
        current_app.logger.error(f"Error getting certifications: {str(e)}")
        return {"error": "Internal server error"}, 500

def update_certifications(certifications_data):
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    supabase: Client = current_app.supabase
    
    try:
        supabase.table("candidate_profiles").update({
            "certifications": json.dumps(certifications_data),
            "updated_at": datetime.now().isoformat()
        }).eq("candidate_id", authenticated_uid).execute()
        return {"success": True}, 200
    except Exception as e:
        current_app.logger.error(f"Error updating certifications: {str(e)}")
        return {"error": "Internal server error"}, 500

# ===== JOB PREFERENCES =====
def get_job_preferences():
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    supabase: Client = current_app.supabase
    
    try:
        response = supabase.table("candidate_profiles").select("job_preferences").eq("candidate_id", authenticated_uid).single().execute()
        job_preferences = json.loads(response.data.get("job_preferences", "{}")) if response.data.get("job_preferences") else {}
        return {"job_preferences": job_preferences}, 200
    except Exception as e:
        current_app.logger.error(f"Error getting job preferences: {str(e)}")
        return {"error": "Internal server error"}, 500

def update_job_preferences(job_preferences_data):
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    supabase: Client = current_app.supabase
    
    try:
        supabase.table("candidate_profiles").update({
            "job_preferences": json.dumps(job_preferences_data),
            "updated_at": datetime.now().isoformat()
        }).eq("candidate_id", authenticated_uid).execute()
        return {"success": True}, 200
    except Exception as e:
        current_app.logger.error(f"Error updating job preferences: {str(e)}")
        return {"error": "Internal server error"}, 500

