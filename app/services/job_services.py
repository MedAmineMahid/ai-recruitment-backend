from supabase.client import Client
from flask import current_app
from typing import List, Dict, Optional, Union
import uuid
import json
from app.db import get_db_connection
from app.utils.auth_utils import get_user_role, get_current_user_id, is_recruiter
from .cv_service import get_cv_by_id
from app.services.matching_service import get_matching_service

def create_job(job_data):
    supabase = get_db_connection()
    try:
        company_id = job_data.get('company_id')
        if not company_id:
            # Attempt to get company_id from authenticated user's context
            current_user_id = get_current_user_id()
            if current_user_id:
                # Assuming there's a way to link user_id to company_id, e.g., in a 'profiles' or 'recruiters' table
                # For now, let's assume the user's company_id is directly available or can be fetched.
                # This is a placeholder for actual logic to retrieve the company_id for the current user.
                # You might need to query the 'profiles' or 'recruiters' table to get the company_id.
                # For demonstration, let's assume a direct mapping or a default if not found.
                # This part needs to be implemented based on your user/company structure.
                # For now, if company_id is not provided in job_data, and cannot be derived, it will raise an error.
                # A more robust solution would involve fetching the company_id from the user's profile.
                # For now, let's raise an error if company_id is missing.
                raise ValueError("Company ID is required and not provided.")
            else:
                raise ValueError("Company ID is required and user not authenticated.")

        # Validate if company_id is a valid UUID if it's not None
        if company_id and not isinstance(company_id, str):
            raise ValueError("Company ID must be a string (UUID).")
        try:
            # Ensure it's a valid UUID
            uuid.UUID(str(company_id))
        except ValueError:
            raise ValueError("Company ID must be a valid UUID.")
        recruiter_id = get_current_user_id()
        if not recruiter_id:
            raise ValueError("Recruiter ID not found. User must be authenticated.")

        data, count = supabase.from_('jobs').insert({
            'recruiter_id': recruiter_id,
            'company_id': company_id,
            'title': job_data['title'],
            'description': job_data['description'],
            'location': job_data['location'],
            'requirements': job_data.get('requirements'),
            'education': job_data.get('education'),
            'contract_type': job_data.get('contract_type'),
            'work_mode': job_data.get('work_mode'),
            'salary_min': job_data.get('salary_min'),
            'salary_max': job_data.get('salary_max'),
            'salary_currency': job_data.get('salary_currency'),
            'skills': job_data.get('skills')
        }).execute()
        if data and data[1]:
            job_id = data[1][0]['id']
            # Trigger AI matching for this new job against all candidates
            matching_service = get_matching_service()
            matching_service.match_job_to_candidates(job_id)
            return {**job_data, "id": job_id, "company_id": company_id}
        else:
            raise Exception("Failed to create job")
    except Exception as e:
        current_app.logger.error(f"Error creating job: {e}")
        raise

def get_jobs_data(filters: Dict[str, Union[str, List[str], int, float]]) -> List[Dict]:
    authenticated_uid = get_current_user_id()
    current_app.logger.info(f"Authenticated UID in get_jobs_data: {authenticated_uid}")
    if not authenticated_uid:
        current_app.logger.warning("No authenticated UID, returning empty jobs list.")
        return []

    supabase: Client = current_app.supabase

    try:
        query = supabase.table("jobs").select("*, company:companies(*), candidate_job_matches!left(match_percentage)")

        if filters.get("recruiter_id"):
            query = query.eq("recruiter_id", filters["recruiter_id"])

        if filters.get("search"):
            search_term = f"%{filters['search']}%"
            query = query.or_(f"title.ilike.{search_term},description.ilike.{search_term}")

        if filters.get("location"):
            query = query.ilike("location", f"%{filters['location']}%")

        if filters.get("contract_type"):
            query = query.eq("contract_type", filters["contract_type"])

        if filters.get("work_mode"):
            query = query.in_("work_mode", filters["work_mode"])

        if filters.get("min_salary"):
            query = query.gte("salary_range", f"\u20ac{filters['min_salary']}")

        page = filters.get("page", 1)
        limit = filters.get("limit", 20)
        offset = (page - 1) * limit
        query = query.range(offset, offset + limit - 1)

        response = query.execute()
        jobs = response.data or []
        current_app.logger.info(f"Supabase query response data: {jobs}")

        formatted_jobs = []
        for job in jobs:
            formatted_jobs.append({
                "id": job["id"],
                "company_id": job["company_id"],
                "title": job["title"],
                "description": job["description"],
                "location": job["location"],
                "requirements": job.get("requirements", []),
                "education": job.get("education", ""),
                "created_at": job["created_at"],
                "company": {
                    "name": job["company"]["name"],
                    "logo_url": job["company"].get("logo_url"),
                    "description": job["company"].get("description", "")
                },
                "contract_type": job.get("contract_type"),
                "work_mode": job.get("work_mode"),
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
                "salary_currency": job.get("salary_currency"),
                "skills": job.get("requirements", [])[:5],
                "match_score": job["candidate_job_matches"][0]["match_percentage"] if job["candidate_job_matches"] else 0
            })

        return formatted_jobs

    except Exception as e:
        current_app.logger.error(f"Error fetching jobs: {str(e)}")
        return []

def get_job_by_id(job_id: str) -> Optional[Dict]:
    authenticated_uid = get_current_user_id()
    if not authenticated_uid:
        current_app.logger.warning(f"Unauthorized access attempt for job {job_id}")
        return None

    supabase: Client = current_app.supabase

    try:
        job_query = supabase.table("jobs").select("*, company:companies(*)").eq("id", job_id)
        job_response = job_query.maybe_single().execute()

        if not job_response.data:
            current_app.logger.info(f"Job not found: {job_id}")
            return None

        job = job_response.data

        try:
            application_response = supabase.table("applications").select("*").match({
                "job_id": job_id,
                "candidate_id": authenticated_uid
            }).maybe_single().execute()
            has_applied = bool(application_response.data)
        except Exception as app_err:
            current_app.logger.error(f"Error checking application status: {str(app_err)}")
            has_applied = False

        match_score = 0
        try:
            match_response = supabase.table("candidate_job_matches").select("match_percentage").eq("candidate_id", authenticated_uid).eq("job_id", job_id).maybe_single().execute()
            if match_response.data:
                match_score = match_response.data.get("match_percentage", 0)
        except Exception as match_err:
            current_app.logger.error(f"Error fetching match score for job {job_id} and candidate {authenticated_uid}: {str(match_err)}")

        return {
            "id": job["id"],
            "company_id": job["company_id"],
            "title": job["title"],
            "description": job["description"],
            "location": job["location"],
            "requirements": job.get("requirements", []),
            "education": job.get("education", ""),
            "created_at": job["created_at"],
            "company": {
                "name": job.get("company", {}).get("name", "Unknown Company"),
                "logo_url": job.get("company", {}).get("logo_url"),
                "description": job.get("company", {}).get("description", "")
            },
            "contract_type": job.get("contract_type"),
            "work_mode": job.get("work_mode"),
            "salary_min": job.get("salary_min"),
            "salary_max": job.get("salary_max"),
            "salary_currency": job.get("salary_currency"),
            "skills": job.get("skills", job.get("requirements", [])[:5]),
            "has_applied": has_applied,
            "match_score": match_score
        }

    except Exception as e:
        current_app.logger.error(f"Error fetching job {job_id}: {str(e)}", exc_info=True)
        return None

def get_candidates_for_job(job_id: str) -> List[Dict]:
    supabase = get_db_connection()
    try:
        # Fetch applications for the given job_id
        applications_response = supabase.from_('applications').select('*, candidates(*, candidate_profiles(*))').eq('job_id', job_id).execute()
        applications = applications_response.data

        candidates = []
        for app in applications:
            candidate_data = app.get('candidates')
            profile_data = app.get('candidate_profiles')

            if candidate_data and profile_data:
                candidates.append({
                    'application_id': app['id'],
                    'status': app['status'],
                    'applied_at': app['created_at'],
                    'candidate_id': candidate_data['id'],
                    'first_name': candidate_data['first_name'],
                    'last_name': candidate_data['last_name'],
                    'email': candidate_data['email'],
                    'headline': profile_data.get('headline'),
                    'bio': profile_data.get('bio'),
                    'experience': profile_data.get('experience'),
                    'candidate_education': profile_data.get('education'),
                    'candidate_skills': profile_data.get('skills'),
                    'resume_url': profile_data.get('resume_url'),
                    'application_status': app.get('status'),
                    'applied_date': app.get('applied_date')
                })
        return candidates
    except Exception as e:
        current_app.logger.error(f"Error fetching candidates for job {job_id}: {e}")
        raise

def get_recommended_jobs() -> List[Dict]:
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return []

    supabase: Client = current_app.supabase

    try:
        profile_response = supabase.table("candidate_profiles").select(
            "py_skills, skillner_skills, added_skills"
        ).eq("candidate_id", authenticated_uid).single().execute()

        profile = profile_response.data or {}
        user_skills = set(
            (profile.get("py_skills", []) or []) +
            (profile.get("skillner_skills", []) or []) +
            (profile.get("added_skills", []) or [])
        )

        jobs_response = supabase.table("jobs").select("*, company:companies(*)").execute()
        jobs = jobs_response.data or []

        recommended_jobs = []
        for job in jobs:
            job_skills = set(job.get("requirements", [])[:10])
            common_skills = user_skills.intersection(job_skills)
            match_score = int((len(common_skills) / max(len(job_skills), 1)) * 100)

            if match_score >= 50:
                recommended_jobs.append({
                    "id": job["id"],
                    "company_id": job["company_id"],
                    "title": job["title"],
                    "description": job["description"],
                    "location": job["location"],
                    "requirements": job.get("requirements", []),
                    "education": job.get("education", ""),
                    "created_at": job["created_at"],
                    "company": {
                        "name": job["company"]["name"],
                        "logo_url": job["company"].get("logo_url"),
                        "description": job["company"].get("description", "")
                    },
                    "contract_type": job.get("contract_type"),
                    "work_mode": job.get("work_mode"),
                    "salary_range": job.get("salary_range"),
                    "skills": list(job_skills),
                    "match_score": match_score,
                    "is_recommended": True
                })

        recommended_jobs.sort(key=lambda x: x["match_score"], reverse=True)
        return recommended_jobs[:20]

    except Exception as e:
        current_app.logger.error(f"Error fetching recommended jobs: {str(e)}")
        return []



def verify_supabase_token():
    return "dummy-user-id"
