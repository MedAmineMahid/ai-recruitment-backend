from app.db import get_db_connection
import uuid

def create_interview(job_id, candidate_id, recruiter_id, interview_time, meeting_link=None):
    supabase = get_db_connection()
    interview_id = str(uuid.uuid4())
    data, count = supabase.from_('interviews').insert({
        'id': interview_id,
        'job_id': job_id,
        'candidate_id': candidate_id,
        'recruiter_id': recruiter_id,
        'interview_time': interview_time,
        'meeting_link': meeting_link
    }).execute()
    if data:
        return interview_id
    else:
        raise Exception("Failed to create interview")

def get_interview(interview_id):
    supabase = get_db_connection()
    data, count = supabase.from_('interviews').select('*').eq('id', interview_id).limit(1).execute()
    if data and data[1]:
        interview = data[1][0]
        return {
            'id': interview['id'],
            'job_id': interview['job_id'],
            'candidate_id': interview['candidate_id'],
            'recruiter_id': interview['recruiter_id'],
            'interview_time': str(interview['interview_time']),
            'status': interview['status'],
            'meeting_link': interview['meeting_link'],
            'created_at': str(interview['created_at']),
            'updated_at': str(interview['updated_at'])
        }
    return None

def update_interview_status(interview_id, status):
    supabase = get_db_connection()
    data, count = supabase.from_('interviews').update({'status': status, 'updated_at': 'now()'}) \
        .eq('id', interview_id).execute()
    if not data:
        raise Exception("Failed to update interview status")

def get_interviews_for_job(job_id):
    supabase = get_db_connection()
    data, count = supabase.from_('interviews').select('*').eq('job_id', job_id).order('interview_time', desc=True).execute()
    if data and data[1]:
        return [{
            'id': interview['id'],
            'job_id': interview['job_id'],
            'candidate_id': interview['candidate_id'],
            'recruiter_id': interview['recruiter_id'],
            'interview_time': str(interview['interview_time']),
            'status': interview['status'],
            'meeting_link': interview['meeting_link'],
            'created_at': str(interview['created_at']),
            'updated_at': str(interview['updated_at'])
        } for interview in data[1]]
    return []

def get_interviews_for_candidate(candidate_id):
    supabase = get_db_connection()
    data, count = supabase.from_('interviews').select('*').eq('candidate_id', candidate_id).order('interview_time', desc=True).execute()
    if data and data[1]:
        return [{
            'id': interview['id'],
            'job_id': interview['job_id'],
            'candidate_id': interview['candidate_id'],
            'recruiter_id': interview['recruiter_id'],
            'interview_time': str(interview['interview_time']),
            'status': interview['status'],
            'meeting_link': interview['meeting_link'],
            'created_at': str(interview['created_at']),
            'updated_at': str(interview['updated_at'])
        } for interview in data[1]]
    return []

def get_interviews_for_recruiter(recruiter_id):
    supabase = get_db_connection()
    data, count = supabase.from_('interviews').select('*').eq('recruiter_id', recruiter_id).order('interview_time', desc=True).execute()
    if data and data[1]:
        return [{
            'id': interview['id'],
            'job_id': interview['job_id'],
            'candidate_id': interview['candidate_id'],
            'recruiter_id': interview['recruiter_id'],
            'interview_time': str(interview['interview_time']),
            'status': interview['status'],
            'meeting_link': interview['meeting_link'],
            'created_at': str(interview['created_at']),
            'updated_at': str(interview['updated_at'])
        } for interview in data[1]]
    return []