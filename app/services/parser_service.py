from flask import current_app, request
from supabase import Client
import json
import os
from datetime import datetime
from .cv_service import verify_supabase_token

def extract_skills(text):
    """
    Extrait les compétences depuis un texte brut avec SkillNER.
    Retourne une liste d'objets contenant des informations sur chaque compétence.
    """
    skill_extractor = current_app.skill_extractor
    SKILL_DB=current_app.SKILL_DB
    # Convert text to lowercase for consistent skill extraction, similar to the notebook's approach
    text_lower = text.lower()
    annotations = skill_extractor.annotate(text_lower)
    skills = []

    # Parcourir les résultats pour tous les types de matching
    # current_app.logger.error(text)

    for type_matching, arr_skills in annotations["results"].items():
        for skill in arr_skills:
            if skill['skill_id'] in SKILL_DB:
                skill_info = SKILL_DB[skill['skill_id']]
                skill_name = skill_info['skill_name']
                skill_type = skill_info.get('skill_type')

                # Only include 'Hard Skill' and 'Soft Skill' types
                if skill_type in ['Hard Skill', 'Soft Skill']:
                    current_app.logger.error(f"Extracted Skill: {skill_name} (Type: {skill_type})")
                    skills.append(skill_name)

    
    return skills

def filter_non_empty(data: dict):
    return {k: v for k, v in data.items() if v not in ("", None, [], {}, "[]", "{}")}



def extract_profile_data():
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    supabase: Client = current_app.supabase
    
    try:
        # Get CV URL
        response = supabase.table("candidate_profiles").select("cv_path").eq("candidate_id", authenticated_uid).execute()
        cv_path = response.data[0].get("cv_path") if response.data else ""

        if not cv_path or not os.path.exists(cv_path):
            return {"error": "CV file not found locally"}, 404

        with open(cv_path, 'rb') as f:
            cv_content = f.read()
        
        # Assuming extract_cv_text can handle raw content and determine type, or we need to pass extension
        # For now, let's assume cv_path implies the original file type or extract_cv_text handles it.
        # If not, we'd need to store the original extension in the DB as well.
        from app.utils.convert_to_text import extract_cv_text
        cv = extract_cv_text(cv_content, cv_path.split('.')[-1]) # Pass content and extension

        
        if not cv:
            return {"error": "CV not found"}, 404
        
        # extract skills with skillner 
        skillner_skills = extract_skills(cv)


        
        # Mock response for male candidate matching both TypeScript and DB structure
        # this parsed data will coming from a function 
        parsed_data = {
            "name": "",
            "title": "",
            "location": "",
            "avatarUrl": "",
            "about": "",
            "experiences": [
                {
                    "title": "",
                    "company": "",
                    "period": "",
                    "location": "",
                    "description": ""
                }
            ],
            "education": [
                {
                    "degree": "",
                    "institution": "",
                    "period": "",
                    "location": "",
                    "description": ""
                }
            ],
            "skills": {
                "extracted": {
                    "pySkills": [],
                    "skillnerSkills": skillner_skills
                },
                "added": []
            },
            "languages": [
                {"name": "", "proficiency": ""}
            ],
            "certifications": [
                {
                    "name": "",
                    "issuingBody": "",
                    "issueDate": "",
                    "credentialUrl": ""
                }
            ],
            "jobPreferences": {
                "isAvailable": True,
                "jobType": "",
                "preferredLocation": "",
                "noticePeriod": ""
            },
            "contact": {
                "email": "",
                "phone": "",
                "linkedin": "",
                "website": "",
                "github": ""
            },
            "cvLastUpdated": datetime.now().isoformat(),
        }
    
    
        profile_updates = {
            "location": parsed_data.get("location", ""),
            "title": parsed_data.get("title", ""),
            "about": parsed_data.get("about", ""),
            "experience": json.dumps( parsed_data.get("experiences", [])),
            "education": json.dumps( parsed_data.get("education", [])),
            "certifications": json.dumps( parsed_data.get("certifications", [])),
            "languages": json.dumps( parsed_data.get("languages", [])),
            "job_preferences": json.dumps( parsed_data.get("jobPreferences", {})),
            "py_skills": parsed_data.get("skills", {}).get("extracted", {}).get("pySkills", []),
            "skillner_skills": parsed_data.get("skills", {}).get("extracted", {}).get("skillnerSkills", []),
            "added_skills": parsed_data.get("skills", {}).get("added", []),
            "linkedin": parsed_data.get("contact", {}).get("linkedin", ""),
            "website": parsed_data.get("contact", {}).get("website", ""),
            "github": parsed_data.get("contact", {}).get("github", ""),
            "updated_at": datetime.now().isoformat()
        }
        
        
        # candidate  updates
        candidates_update = {
            "full_name": parsed_data.get("name", ""),
            "phone": parsed_data.get("contact", {}).get("phone", ""),
        }

        # Filtrer les valeurs non vides
        filtered_candidates_update = filter_non_empty(candidates_update)

        if filtered_candidates_update:
            supabase.table("candidates") \
                    .update(filtered_candidates_update) \
                    .eq("id", authenticated_uid) \
                    .execute()
            
        # candidate profile
        # Filtrer les champs non vides
        filtered_profile_updates = filter_non_empty(profile_updates)

        if filtered_profile_updates:
            supabase.table("candidate_profiles") \
                    .update(filtered_profile_updates) \
                    .eq("candidate_id", authenticated_uid) \
                    .execute()
                    
                    
                    
        return {"message": "Profile updated successfully."}, 200

            
    except Exception as e:
        current_app.logger.error(f"Error extracting profile data: {str(e)}")
        return {"error": "Internal server error"}, 500