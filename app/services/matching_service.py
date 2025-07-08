from flask import current_app
from supabase import Client
from .hybrid_ai_service import get_hybrid_ai_service
from app.utils.auth_utils import verify_supabase_token
from typing import List, Dict, Any, Optional
import json

class MatchingService:
    """
    Service for matching candidates to jobs using hybrid AI approach.
    """
    
    def __init__(self):
        self.hybrid_ai = get_hybrid_ai_service()
    
    def match_candidate_to_jobs(self, candidate_id: str, job_ids: Optional[List[str]] = None, limit: int = 10, filter_by_prediction: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Match a candidate to jobs using hybrid AI scoring.
        
        Args:
            candidate_id: UUID of the candidate
            job_ids: Optional list of specific job IDs to match against
            limit: Maximum number of jobs to return
            
        Returns:
            List of job matches with scores and details
        """
        try:
            supabase: Client = current_app.supabase
            
            # Get candidate profile and CV
            candidate_response = supabase.table("candidate_profiles").select(
                "cv_path, skillner_skills, experience, education"
            ).eq("candidate_id", candidate_id).execute()
            
            if not candidate_response.data:
                return []
            
            candidate_data = candidate_response.data[0]
            
            # Construct candidate text from available data
            cv_text = candidate_data.get('cv_path', '')
            skills = candidate_data.get('skillner_skills', [])
            experience = candidate_data.get('experience', '[]')
            education = candidate_data.get('education', '[]')
            
            # Parse JSON fields if they're strings
            if isinstance(experience, str):
                try:
                    experience = json.loads(experience)
                except:
                    experience = []
            
            if isinstance(education, str):
                try:
                    education = json.loads(education)
                except:
                    education = []
            
            # Combine all candidate information
            candidate_text_parts = [cv_text]
            
            if skills:
                candidate_text_parts.append(' '.join(skills))
            
            for exp in experience:
                if isinstance(exp, dict):
                    candidate_text_parts.extend([
                        exp.get('title', ''),
                        exp.get('company', ''),
                        exp.get('description', '')
                    ])
            
            for edu in education:
                if isinstance(edu, dict):
                    candidate_text_parts.extend([
                        edu.get('degree', ''),
                        edu.get('institution', ''),
                        edu.get('description', '')
                    ])
            
            candidate_text = ' '.join(filter(None, candidate_text_parts))
            
            # Get jobs to match against
            jobs_query = supabase.table("jobs").select(
                "id, title, description, requirements, location, company_id"
            )
            
            if job_ids:
                jobs_query = jobs_query.in_("id", job_ids)
            
            jobs_response = jobs_query.limit(limit * 2).execute()  # Get more to filter
            
            if not jobs_response.data:
                return []
            
            results = []
            
            for job in jobs_response.data:
                # Combine job information
                job_text_parts = [
                    job.get('title', ''),
                    job.get('description', ''),
                    job.get('location', '')
                ]
                
                requirements = job.get('requirements', [])
                if requirements:
                    job_text_parts.append(' '.join(requirements))
                
                job_text = ' '.join(filter(None, job_text_parts))
                
                # Calculate hybrid matching score
                match_result = self.hybrid_ai.calculate_hybrid_score(
                    candidate_text, job_text
                )
                
                # Get company information
                company_info = {}
                if job.get('company_id'):
                    company_response = supabase.table("companies").select(
                        "name, logo_url"
                    ).eq("id", job['company_id']).execute()
                    
                    if company_response.data:
                        company_info = company_response.data[0]
                
                results.append({
                    'job_id': job['id'],
                    'job_title': job.get('title', ''),
                    'job_description': job.get('description', ''),
                    'job_location': job.get('location', ''),
                    'job_requirements': job.get('requirements', []),
                    'company_name': company_info.get('name', ''),
                    'company_logo': company_info.get('logo_url', ''),
                    'match_score': match_result['hybrid_score'],
                    'sbert_similarity': match_result['sbert_similarity'],
                    'skill2vec_similarity': match_result['skill2vec_similarity'],
                    'matched_skills': list(set(match_result['resume_skills']) & set(match_result['job_skills'])),
                    'candidate_skills': match_result['resume_skills'],
                    'job_skills': match_result['job_skills'],
                    'prediction': match_result['hybrid_prediction'],
                    'match_percentage': round(match_result['hybrid_score'] * 100, 2)
                })
            
            # Sort by match score descending
            results.sort(key=lambda x: x['match_score'], reverse=True)

            # Filter by prediction if specified
            if filter_by_prediction:
                results = [r for r in results if r['prediction'] == filter_by_prediction]
            
            # Store results in candidate_job_matches table
            # Delete all existing matches for this candidate before inserting new ones
            try:
                delete_response = supabase.table("candidate_job_matches").delete().eq("candidate_id", candidate_id).execute()
                if hasattr(delete_response, 'error') and delete_response.error:
                    current_app.logger.error(f"Failed to delete previous matches for candidate {candidate_id}: {delete_response.error}")
                else:
                    current_app.logger.info(f"Successfully deleted previous matches for candidate {candidate_id} before inserting new ones.")
            except Exception as e:
                current_app.logger.error(f"Error deleting previous matches for candidate {candidate_id}: {str(e)}", exc_info=True)

            for match in results:
                try:
                    supabase.table("candidate_job_matches").insert({
                        "candidate_id": candidate_id,
                        "job_id": match['job_id'],
                        "match_score": match['match_score'],
                        "sbert_similarity": match['sbert_similarity'],
                        "skill2vec_similarity": match['skill2vec_similarity'],
                        "matched_skills": match['matched_skills'],
                        "candidate_skills": match['candidate_skills'],
                        "job_skills": match['job_skills'],
                        "prediction": match['prediction'],
                        "match_percentage": match['match_percentage']
                    }).execute()
                except Exception as db_e:
                    current_app.logger.error(f"Error storing match for candidate {candidate_id} and job {match['job_id']}: {str(db_e)}")

            return results[:limit]
            
        except Exception as e:
            current_app.logger.error(f"Error in candidate job matching: {str(e)}")
            return []


    
    def match_job_to_candidates(self, job_id: str, candidate_ids: Optional[List[str]] = None,
                               limit: int = 10) -> List[Dict[str, Any]]:
        """
        Match a job to candidates using hybrid AI scoring.
        
        Args:
            job_id: UUID of the job
            candidate_ids: Optional list of specific candidate IDs to match against
            limit: Maximum number of candidates to return
            
        Returns:
            List of candidate matches with scores and details
        """
        try:
            supabase: Client = current_app.supabase

            # Get job details
            job_response = supabase.table("jobs").select(
                "id, title, description, requirements, location"
            ).eq("id", job_id).execute()

            if not job_response.data:
                current_app.logger.warning(f"Job {job_id} not found for matching.")
                return []

            job_data = job_response.data[0]

            # Construct job text
            job_text_parts = [
                job_data.get('title', ''),
                job_data.get('description', ''),
                job_data.get('location', '')
            ]
            requirements = job_data.get('requirements', [])
            if requirements:
                job_text_parts.append(' '.join(requirements))
            job_text = ' '.join(filter(None, job_text_parts))

            # Get candidates to match against
            candidates_query = supabase.table("candidate_profiles").select(
                "candidate_id, cv_path, skillner_skills, experience, education"
            )

            if candidate_ids:
                candidates_query = candidates_query.in_("candidate_id", candidate_ids)

            candidates_response = candidates_query.execute()

            if not candidates_response.data:
                current_app.logger.info(f"No candidates found for matching job {job_id}.")
                return []

            results = []

            # Delete all existing matches for this job before inserting new ones
            try:
                delete_response = supabase.table("candidate_job_matches").delete().eq("job_id", job_id).execute()
                if hasattr(delete_response, 'error') and delete_response.error:
                    current_app.logger.error(f"Failed to delete previous matches for job {job_id}: {delete_response.error}")
                else:
                    current_app.logger.info(f"Successfully deleted previous matches for job {job_id} before inserting new ones.")
            except Exception as e:
                current_app.logger.error(f"Error deleting previous matches for job {job_id}: {str(e)}", exc_info=True)

            for candidate in candidates_response.data:
                # Construct candidate text
                cv_text = candidate.get('cv_path', '')
                skills = candidate.get('skillner_skills', [])
                experience = candidate.get('experience', '[]')
                education = candidate.get('education', '[]')

                if isinstance(experience, str):
                    try:
                        experience = json.loads(experience)
                    except:
                        experience = []

                if isinstance(education, str):
                    try:
                        education = json.loads(education)
                    except:
                        education = []

                candidate_text_parts = [cv_text]
                if skills:
                    candidate_text_parts.append(' '.join(skills))
                for exp in experience:
                    if isinstance(exp, dict):
                        candidate_text_parts.extend([
                            exp.get('title', ''),
                            exp.get('company', ''),
                            exp.get('description', '')
                        ])
                for edu in education:
                    if isinstance(edu, dict):
                        candidate_text_parts.extend([
                            edu.get('degree', ''),
                            edu.get('institution', ''),
                            edu.get('description', '')
                        ])
                candidate_text = ' '.join(filter(None, candidate_text_parts))

                # Calculate hybrid matching score
                match_result = self.hybrid_ai.calculate_hybrid_score(
                    candidate_text, job_text
                )

                match_data = {
                    'candidate_id': candidate['candidate_id'],
                    'job_id': job_id,
                    'match_score': match_result['hybrid_score'],
                    'sbert_similarity': match_result['sbert_similarity'],
                    'skill2vec_similarity': match_result['skill2vec_similarity'],
                    'matched_skills': list(set(match_result['resume_skills']) & set(match_result['job_skills'])),
                    'candidate_skills': match_result['resume_skills'],
                    'job_skills': match_result['job_skills'],
                    'prediction': match_result['hybrid_prediction'],
                    'match_percentage': round(match_result['hybrid_score'] * 100, 2)
                }
                results.append(match_data)

                # Store results in candidate_job_matches table
                try:
                    supabase.table("candidate_job_matches").insert(match_data).execute()
                except Exception as db_e:
                    current_app.logger.error(f"Error storing match for job {job_id} and candidate {candidate['candidate_id']}: {str(db_e)}")

            # Sort by match score descending and return limited results
            results.sort(key=lambda x: x['match_score'], reverse=True)
            return results[:limit]

        except Exception as e:
            current_app.logger.error(f"Error in job to candidate matching: {str(e)}")
            return []
    def get_skill_recommendations(self, candidate_id: str, target_job_id: str) -> Dict[str, Any]:
        """
        Get skill recommendations for a candidate based on a target job.
        
        Args:
            candidate_id: UUID of the candidate
            target_job_id: UUID of the target job
            
        Returns:
            Dictionary with skill gap analysis and recommendations
        """
        try:
            supabase: Client = current_app.supabase
            
            # Get candidate skills
            candidate_response = supabase.table("candidate_profiles").select(
                "skills"
            ).eq("candidate_id", candidate_id).execute()
            
            if not candidate_response.data:
                return {'error': 'Candidate not found'}
            
            candidate_skills = set(candidate_response.data[0].get('skills', []))
            
            # Get job requirements
            job_response = supabase.table("jobs").select(
                "title, description, requirements"
            ).eq("id", target_job_id).execute()
            
            if not job_response.data:
                return {'error': 'Job not found'}
            
            job_data = job_response.data[0]
            job_text = f"{job_data.get('title', '')} {job_data.get('description', '')} {' '.join(job_data.get('requirements', []))}"
            
            # Extract required skills from job
            required_skills = set(self.hybrid_ai.extract_skills_dict(job_text))
            
            # Calculate skill gaps
            missing_skills = required_skills - candidate_skills
            matching_skills = required_skills & candidate_skills
            
            return {
                'candidate_skills': list(candidate_skills),
                'required_skills': list(required_skills),
                'matching_skills': list(matching_skills),
                'missing_skills': list(missing_skills),
                'skill_match_percentage': round((len(matching_skills) / len(required_skills)) * 100, 2) if required_skills else 0,
                'recommendations': {
                    'priority_skills': list(missing_skills)[:5],  # Top 5 missing skills
                    'skill_gap_count': len(missing_skills),
                    'strengths': list(matching_skills)[:5]  # Top 5 matching skills
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting skill recommendations: {str(e)}")
            return {'error': str(e)}

# Global instance
matching_service = None

def get_matching_service() -> MatchingService:
    """Get or create the global matching service instance."""
    global matching_service
    if matching_service is None:
        matching_service = MatchingService()
    return matching_service

def match_candidate_to_jobs_authenticated(job_ids: Optional[List[str]] = None, limit: int = 10, filter_by_prediction: Optional[str] = None) -> tuple:
    """
    Match authenticated candidate to jobs.
    
    Returns:
        Tuple of (result, status_code)
    """
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401
    
    try:
        service = get_matching_service()
        matches = service.match_candidate_to_jobs(authenticated_uid, job_ids, limit, filter_by_prediction)
        
        return {
            "matches": matches,
            "total_matches": len(matches),
            "candidate_id": authenticated_uid
        }, 200
        
    except Exception as e:
        current_app.logger.error(f"Error in authenticated job matching: {str(e)}")
        return {"error": "Internal server error"}, 500

def get_skill_recommendations_authenticated(target_job_id: str) -> tuple:
    """
    Get skill recommendations for authenticated candidate.
    
    Returns:
        Tuple of (result, status_code)
    """
    authenticated_uid = verify_supabase_token()
    if not authenticated_uid:
        return {"error": "Unauthorized"}, 401
    
    try:
        service = get_matching_service()
        recommendations = service.get_skill_recommendations(authenticated_uid, target_job_id)
        
        if 'error' in recommendations:
            return recommendations, 404
        
        return recommendations, 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting skill recommendations: {str(e)}")
        return {"error": "Internal server error"}, 500