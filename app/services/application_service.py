from datetime import datetime
from flask import current_app, request
from supabase import Client, StorageException
from app.utils.auth_utils import get_current_user_id, verify_supabase_token
from datetime import datetime
# ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}

# def allowed_file(filename: str) -> bool:
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# def upload_custom_cv(uid: str, job_id: str, file) -> str | None:
#     supabase: Client = current_app.supabase
    
#     if not allowed_file(file.filename):
#         return None

#     extension = file.filename.rsplit('.', 1)[1].lower()
#     filename = secure_filename(f"{uid}/applications/{job_id}/cv.{extension}")

#     try:
#         file_content = file.read()
        
#         # Delete existing CV if it exists
#         existing_files = supabase.storage.from_("cvs").list(f"{uid}/applications/{job_id}")
#         if existing_files:
#             supabase.storage.from_("cvs").remove([filename])

#         supabase.storage.from_("cvs").upload(
#             path=filename,
#             file=file_content,
#             file_options={
#                 "content-type": file.mimetype,
#                 "x-upsert": "true"
#             }
#         )

#         return supabase.storage.from_("cvs").get_public_url(filename)
#     except Exception as e:
#         current_app.logger.error(f"Error uploading custom CV: {str(e)}")
#         return None



def create_application():
    authenticated_uid = get_current_user_id()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    try:
        # Validate request data
        if not request.form:
            return {"error": "No form data provided"}, 400

        data = request.form
        job_id = data.get("job_id")

        # cv_option = data.get("cv_option")  # 'default' or 'custom'
        
        if not job_id:
            return {"error": "Job ID is required"}, 400
        # if cv_option not in ['default', 'custom']:
        #     return {"error": "Invalid CV option"}, 400

        supabase: Client = current_app.supabase
        
        # 1. Check for existing application - Improved version
        try:
            existing_response = supabase.rpc(
                'check_existing_application',
                {
                    'p_job_id': job_id,
                    'p_candidate_id': authenticated_uid
                }
            ).execute()
            
            current_app.logger.error(f"existing_response : {str(existing_response.data[0].get('is_existing'))}")


            if existing_response.data and existing_response.data[0].get('is_existing'):
                return {
                    "error": "Application already exists",
                    "application_id": existing_response.data[0].get('application_id')
                }, 409

        except Exception as e:
            current_app.logger.error(f"Supabase RPC error: {str(e)}")
            # Fallback to direct query if RPC fails
            current_app.logger.error(f"Fallback to direct query if RPC fails : {str(existing_response)}")

            try:
                existing_app = supabase.table("applications") \
                    .select("id") \
                    .eq("job_id", job_id) \
                    .eq("candidate_id", authenticated_uid) \
                .single() \
                .execute()
                return existing_app.data[0], 201
            except Exception as e_fallback:
                current_app.logger.error(f"Error during direct query fallback: {str(e_fallback)}")
                return {"error": "Failed to create application during fallback"}, 500

        # If no existing application, proceed to create a new one
        # Handle CV upload based on option
        # cv_path = None
        # if cv_option == 'default':
        #     # Fetch default CV path from user's profile or a predefined location
        #     # For now, let's assume a default CV path can be retrieved
        #     # This needs to be implemented based on how default CVs are managed
        #     try:
        #         candidate_profile = supabase.table('candidate_profiles').select('cv_path').eq('candidate_id', authenticated_uid).single().execute()
        #         if candidate_profile.data and candidate_profile.data['cv_path']:
        #             cv_path = candidate_profile.data['cv_path']
        #         else:
        #             return {"error": "Default CV not found for candidate"}, 404
        #     except Exception as e:
        #         current_app.logger.error(f"Error fetching default CV path: {str(e)}")
        #         return {"error": "Failed to retrieve default CV"}, 500
        # elif cv_option == 'custom':
        #     if 'cv_file' not in request.files:
        #         return {"error": "No CV file provided"}, 400
        #     cv_file = request.files['cv_file']
        #     if cv_file.filename == '':
        #         return {"error": "No selected CV file"}, 400
        #     cv_path = upload_file(cv_file, authenticated_uid, 'cv')
        #     if not cv_path:
        #         return {"error": "Failed to upload CV"}, 500



        # Create application entry in Supabase
        try:
            application_data = {
                "candidate_id": authenticated_uid,
                "job_id": job_id,
                "created_at": datetime.now().isoformat(),
                "status": "Applied", # Initial status
            }
            new_application = supabase.table("applications").insert(application_data).execute()
            if new_application.data:
                return {"message": "Application created successfully", "application_id": new_application.data[0]['id']}, 201
            else:
                current_app.logger.error(f"Supabase insert failed: {new_application.error}")
                return {"error": "Failed to create application"}, 500
        except Exception as e:
            current_app.logger.error(f"Error inserting application into Supabase: {str(e)}")
            return {"error": "Failed to create application"}, 500

    except Exception as e:
        current_app.logger.error(f"Error creating application: {str(e)}")
        return {"error": "Failed to create application"}, 500

def update_application_status(application_id: str):
    authenticated_uid = get_current_user_id()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    try:
        data = request.get_json()
        new_status = data.get("status")

        if not new_status:
            return {"error": "New status is required"}, 400

        supabase: Client = current_app.supabase

        # Verify that the application belongs to a job posted by the authenticated recruiter
        # Or that the authenticated user is the candidate for the application
        application_data = supabase.table("applications") \
            .select("job_id, candidate_id") \
            .eq("id", application_id) \
            .maybe_single() \
            .execute()

        if not application_data.data:
            return {"error": "Application not found"}, 404

        job_id = application_data.data["job_id"]
        candidate_id = application_data.data["candidate_id"]

        is_recruiter_of_job = False
        is_candidate_of_application = False

        # Check if authenticated user is the recruiter who posted the job
        recruiter_job = supabase.table("jobs") \
            .select("recruiter_id") \
            .eq("id", job_id) \
            .eq("recruiter_id", authenticated_uid) \
            .maybe_single() \
            .execute()

        if recruiter_job.data:
            is_recruiter_of_job = True

        # Check if authenticated user is the candidate for this application
        if candidate_id == authenticated_uid:
            is_candidate_of_application = True

        if not (is_recruiter_of_job or is_candidate_of_application):
            return {"error": "Forbidden: You do not have permission to update this application's status"}, 403

        # Update the application status
        response = supabase.table("applications") \
            .update({"status": new_status}) \
            .eq("id", application_id) \
            .execute()

        if not response.data or len(response.data) == 0:
            raise ValueError("No data returned from update operation")

        return response.data[0], 200

    except Exception as e:
        current_app.logger.error(f"Error updating application status: {str(e)}")
        return {"error": "Failed to update application status"}, 500



        # Get default CV URL with error handling
        # try:
        #     profile = supabase.table("candidate_profiles") \
        #         .select("cv_path") \
        #         .eq("candidate_id", authenticated_uid) \
        #         .maybe_single() \
        #         .execute()
                
        #     default_cv_url = profile.data.get("cv_path") if profile.data else candidate_data.get("cv_url")
        # except Exception as e:
        #     current_app.logger.error(f"Error fetching candidate profile: {str(e)}")
        #     default_cv_url = candidate_data.get("cv_url")

        # Handle file uploads with better validation
        custom_cv_url = None
        if cv_option == 'custom' and 'custom_cv' in request.files:
            custom_cv = request.files['custom_cv']
            if custom_cv and custom_cv.filename != '':
                if not allowed_file(custom_cv.filename):
                    return {"error": "Invalid CV file type"}, 400
                
                custom_cv_url = upload_custom_cv(authenticated_uid, job_id, custom_cv)
                if not custom_cv_url:
                    return {"error": "Failed to upload custom CV"}, 500

        cover_letter_file_url = None
        if 'cover_letter_file' in request.files:
            cover_letter_file = request.files['cover_letter_file']
            if cover_letter_file and cover_letter_file.filename != '':
                if not allowed_file(cover_letter_file.filename):
                    return {"error": "Invalid cover letter file type"}, 400
                    
                cover_letter_file_url = upload_cover_letter_file(authenticated_uid, job_id, cover_letter_file)
                if not cover_letter_file_url:
                    return {"error": "Failed to upload cover letter"}, 500

        # Create application record with better error handling
        application_data = {
            "job_id": job_id,
            "candidate_id": authenticated_uid,
            "status": "pending",
            "custom_cv_url": custom_cv_url,
            "cover_letter_text": cover_letter_text,
            "cover_letter_file_url": cover_letter_file_url,
            "applied_at": datetime.datetime.utcnow().isoformat(),
            "cv_last_updated": datetime.datetime.utcnow().isoformat() if custom_cv_url else None
        }

        try:
            response = supabase.table("applications") \
                .insert(application_data) \
                .execute()

            if not response.data or len(response.data) == 0:
                raise ValueError("No data returned from insert operation")

            match_response = supabase.table("candidate_job_matches")\
                .select("match_percentage")\
                .eq("candidate_id", authenticated_uid)\
                .eq("job_id", application_data["job_id"])\
                .maybe_single()\
                .execute()

            match_percentage = match_response.data.get("match_percentage") if match_response.data else 0

            # Update the application with the match percentage
            supabase.table("applications")\
                .update({"match_percentage": match_percentage})\
                .eq("id", response.data[0]["id"])\
                .execute()

            return {"message": "Application created successfully", "application_id": response.data[0]["id"]}, 201

        except Exception as e:
            current_app.logger.error(f"Error inserting application: {str(e)}")
            return {"error": "Failed to create application"}, 500

    except Exception as e:
        current_app.logger.error(f"Unexpected error in create_application: {str(e)}")
        return {"error": "Internal server error"}, 500

def update_application_status(application_id):
    authenticated_uid = get_current_user_id()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    try:
        data = request.json
        new_status = data.get("status")

        if not new_status:
            return {"error": "New status is required"}, 400

        supabase: Client = current_app.supabase

        # Check if the application exists and belongs to a job posted by the current recruiter
        application_response = supabase.table("applications") \
            .select("job_id") \
            .eq("id", application_id) \
            .maybe_single() \
            .execute()

        if not application_response.data:
            return {"error": "Application not found"}, 404

        job_id = application_response.data.get("job_id")

        job_response = supabase.table("jobs") \
            .select("recruiter_id") \
            .eq("id", job_id) \
            .eq("recruiter_id", authenticated_uid) \
            .maybe_single() \
            .execute()

        if not job_response.data:
            return {"error": "Job not found or you don't have permission to update this application"}, 403

        # Update the application status
        response = supabase.table("applications") \
            .update({"status": new_status}) \
            .eq("id", application_id) \
            .execute()

        if not response.data:
            raise ValueError("No data returned from update operation")

        return {"message": "Application status updated successfully", "application": response.data[0]}, 200

    except Exception as e:
        current_app.logger.error(f"Error updating application status: {str(e)}")
        return {"error": "Failed to update application status"}, 500

    except Exception as e:
        current_app.logger.error(f"Error inserting application: {str(e)}")
        return {"error": "Failed to create application"}, 500

    except Exception as e:
        current_app.logger.error(f"Unexpected error in create_application: {str(e)}")
        return {"error": "Internal server error"}, 500

def get_user_applications(candidate_id: str):
    authenticated_uid = get_current_user_id()
    if not authenticated_uid or authenticated_uid != candidate_id:
        return {"error": "Unauthorized"}, 401

    supabase: Client = current_app.supabase

    try:
        response = supabase.table("applications")\
            .select("*, job:jobs(*, company:companies(*))")\
            .eq("candidate_id", candidate_id)\
            .order("applied_at", desc=True).execute()

        applications = response.data if response.data is not None else []
        if not applications:
            return {"applications": []}, 200

        formatted_applications = []
        for app in applications:
            job = app.get("job")
            if job:
                formatted_applications.append({
                    "id": app["id"],
                    "job_id": app["job_id"],
                    "candidate_id": app["candidate_id"],
                    "status": app["status"],
                    "applied_at": app["applied_at"],
                    "match_percentage": app.get("match_percentage"),
                    "job_title": job.get("job_title"),
                    "company_name": job.get("company", {}).get("name"),
                    "company_logo_url": job.get("company", {}).get("logo_url"),
                    "job_location": job.get("job_location"),
                    "job_type": job.get("job_type"),
                    "salary_min": job.get("salary_min"),
                    "salary_max": job.get("salary_max"),
                    "salary_currency": job.get("salary_currency"),
                    "job_description": job.get("job_description"),
                    "responsibilities": job.get("responsibilities"),
                    "requirements": job.get("requirements"),
                    "benefits": job.get("benefits"),
                    "posted_at": job.get("posted_at"),
                    "expires_at": job.get("expires_at"),
                    "external_url": job.get("external_url"),
                    "job_status": job.get("job_status"),
                    "company_id": job.get("company_id"),
                })
        return {"applications": formatted_applications}, 200

    except Exception as e:
        current_app.logger.error(f"Error fetching user applications: {str(e)}")
        return {"error": "Internal server error"}, 500



def update_application(application_id):
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    try:
        data = request.form
        cover_letter_text = data.get("cover_letter_text")
        cv_option = data.get("cv_option")  # 'default' or 'custom'
        
        supabase: Client = current_app.supabase
        
        # First get the existing application to verify ownership
        existing_app = supabase.table("applications").select("*").eq("id", application_id).single().execute()
        if hasattr(existing_app, 'error') or not existing_app.data:
            return {"error": "Application not found"}, 404
            
        if existing_app.data["candidate_id"] != authenticated_uid:
            return {"error": "Unauthorized - you can only update your own applications"}, 403
            
        # Check if application status allows updates
        if existing_app.data["status"] not in ["pending", "draft"]:
            return {"error": "Cannot update application - status is not editable"}, 400

        # Handle custom CV upload
        custom_cv_url = existing_app.data["custom_cv_url"]
        if cv_option == 'custom' and 'custom_cv' in request.files:
            custom_cv = request.files['custom_cv']
            if custom_cv.filename != '':
                custom_cv_url = upload_custom_cv(authenticated_uid, existing_app.data["job_id"], custom_cv)
                if not custom_cv_url:
                    return {"error": "Failed to upload custom CV"}, 500

        # Handle cover letter file upload
        cover_letter_file_url = existing_app.data["cover_letter_file_url"]
        if 'cover_letter_file' in request.files:
            cover_letter_file = request.files['cover_letter_file']
            if cover_letter_file.filename != '':
                cover_letter_file_url = upload_cover_letter_file(authenticated_uid, existing_app.data["job_id"], cover_letter_file)
                if not cover_letter_file_url:
                    return {"error": "Failed to upload cover letter"}, 500

        # Update application record
        update_data = {
            "custom_cv_url": custom_cv_url,
            "cover_letter_text": cover_letter_text or existing_app.data["cover_letter_text"],
            "cover_letter_file_url": cover_letter_file_url,
            "cv_last_updated": datetime.datetime.utcnow().isoformat() if custom_cv_url else existing_app.data["cv_last_updated"],
            "updated_at": datetime.datetime.utcnow().isoformat()
        }

        response = supabase.table("applications").update(update_data).eq("id", application_id).execute()
        
        if hasattr(response, 'error') and response.error:
            return {"error": "Failed to update application"}, 500

        return {"success": True, "application_id": application_id}, 200

    except Exception as e:
        current_app.logger.error(f"Error updating application: {str(e)}")
        return {"error": "Internal server error"}, 500
    


def get_job_applications(job_id):
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    # Here you might want to verify the user has permission to see these applications
    # For example, check if they're the job poster or an admin

    try:
        supabase: Client = current_app.supabase
        response = supabase.table("applications").select("*").eq("job_id", job_id).execute()
        
        if hasattr(response, 'error') and response.error:
            return {"error": "Failed to fetch applications"}, 500

        return {"applications": response.data}, 200
    except Exception as e:
        current_app.logger.error(f"Error getting job applications: {str(e)}")
        return {"error": "Internal server error"}, 500
    

def get_application(application_id):
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    try:
        supabase: Client = current_app.supabase
        
        # First get the application
        response = supabase.table("applications").select("*").eq("id", application_id).single().execute()
        
        if hasattr(response, 'error') and response.error:
            return {"error": "Application not found"}, 404

        application = response.data
        
        # Verify the user has permission to view this application
        if application["candidate_id"] != authenticated_uid:
            # Check if user is the job poster or admin
            job_response = supabase.table("jobs").select("posted_by").eq("id", application["job_id"]).single().execute()
            if hasattr(job_response, 'error') or job_response.data["posted_by"] != authenticated_uid:
                return {"error": "Unauthorized"}, 403

        return {"application": application}, 200
    except Exception as e:
        current_app.logger.error(f"Error getting application: {str(e)}")
        return {"error": "Internal server error"}, 500
    
    
    
    
    
def delete_application(application_id):
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401

    try:
        supabase: Client = current_app.supabase
        
        # First verify the application exists and belongs to the user
        existing_app = supabase.table("applications") \
            .select("*") \
            .eq("id", application_id) \
            .maybe_single() \
            .execute()
       
        if not existing_app.data:
            return {"error": "Application not found"}, 404
            
        # Delete associated files if they exist
        try:
            if existing_app.data.get("custom_cv_url"):
                # Extract path from URL or construct it
                path = f"{existing_app.data['candidate_id']}/applications/{existing_app.data['job_id']}/cv.*"
                supabase.storage.from_("cvs").remove([path])
                
            if existing_app.data.get("cover_letter_file_url"):
                path = f"{existing_app.data['candidate_id']}/applications/{existing_app.data['job_id']}/cover_letter.*"
                supabase.storage.from_("coverletters").remove([path])
            
            current_app.logger.error(f"existing_app: {str(existing_app)}")
        except Exception as storage_error:
            current_app.logger.error(f"Error deleting storage files: {str(storage_error)}")
            # Continue with application deletion even if file deletion fails

        # Delete the application record
        response = supabase.table("applications") \
            .delete() \
            .eq("id", application_id) \
            .execute()
            
        # Check if the deletion was successful
        if hasattr(response, 'data') and response.data:
            # In Supabase-py, a successful DELETE returns the deleted records
            return {"success": True, "message": "Application deleted"}, 200
        else:
            # Handle cases where the response is empty but the deletion was successful
            # Verify the application no longer exists
            check_app = supabase.table("applications") \
                .select("*") \
                .eq("id", application_id) \
                .maybe_single() \
                .execute()
                
            if not check_app.data:
                return {"success": True, "message": "Application deleted"}, 200
            else:
                current_app.logger.error(f"Supabase deletion failed: {str(response)}")
                return {"error": "Failed to delete application"}, 500

    except Exception as e:
        current_app.logger.error(f"Error deleting application: {str(e)}")
        return {"error": "Internal server error"}, 500
    
    
    