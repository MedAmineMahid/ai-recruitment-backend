from app.db import get_db_connection
import json

def get_recruiter_dashboard_data(recruiter_id):
    conn = get_db_connection()
    
    # Get jobs for this recruiter directly
    jobs_response = conn.from_('jobs')\
        .select('id, title')\
        .eq('recruiter_id', recruiter_id)\
        .execute()
    jobs = jobs_response.data
    
    job_data = []
    for job in jobs:
        job_id = job['id']
        job_title = job['title']
        
        # Get candidates who applied for this job
        # Using Supabase's PostgreSQL query feature
        candidates_response = conn.from_('applications')\
            .select(
                'id, candidate_id:candidate_id, status:status, '
                'candidates!inner(id, full_name), score'
            )\
            .eq('job_id', job_id)\
            .execute()
        
        candidates = candidates_response.data
        
        # Process candidates data to normalize structure
        processed_candidates = []
        for c in candidates:
            # Handle the nested structure from Supabase
            candidate = {
                'application_id': c.get('id'),
                'candidate_id': c.get('candidate_id'),
                'application_status': c.get('status', 'pending'),
                'match_score': None
            }
            
            # Extract candidate info from nested structure
            if 'candidates' in c and c['candidates']:
                candidate_info = c['candidates']
                full_name = candidate_info.get('full_name', '')
                name_parts = full_name.split(' ', 1)
                candidate['first_name'] = name_parts[0] if name_parts else ''
                candidate['last_name'] = name_parts[1] if len(name_parts) > 1 else ''
            
            # Extract match score from nested structure
            candidate['match_score'] = c.get('score')
            
            processed_candidates.append(candidate)
        
        # Calculate stats for this job
        total_applications = len(processed_candidates)
        accepted_applications = sum(1 for c in processed_candidates if c['application_status'] == 'accepted')
        rejected_applications = sum(1 for c in processed_candidates if c['application_status'] == 'rejected')
        pending_applications = sum(1 for c in processed_candidates if c['application_status'] == 'pending')
        
        # Get best matches (e.g., top 5 by match_score)
        best_matches = sorted([c for c in processed_candidates if c['match_score'] is not None], 
                              key=lambda x: x['match_score'], reverse=True)[:5]
        
        job_data.append({
            'job_id': job_id,
            'job_title': job_title,
            'total_applications': total_applications,
            'accepted_applications': accepted_applications,
            'rejected_applications': rejected_applications,
            'pending_applications': pending_applications,
            'candidates': processed_candidates,
            'best_matches': best_matches
        })
    
    # No need to close connection with Supabase client
    
    return {
        'jobs': job_data
    }