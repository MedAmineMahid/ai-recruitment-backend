from app.db import get_db_connection
import uuid

def create_message(sender_id, receiver_id, job_id, content):
    supabase = get_db_connection()
    message_id = str(uuid.uuid4())
    data, count = supabase.from_('messages').insert({
        'id': message_id,
        'sender_id': sender_id,
        'receiver_id': receiver_id,
        'job_id': job_id,
        'content': content
    }).execute()
    if data:
        return message_id
    else:
        raise Exception("Failed to create message")

def get_messages_between_users(user1_id, user2_id):
    supabase = get_db_connection()
    data, count = supabase.from_('messages').select('*').or_(f'and(sender_id.eq.{user1_id},receiver_id.eq.{user2_id}),and(sender_id.eq.{user2_id},receiver_id.eq.{user1_id})').order('created_at', desc=False).execute()
    if data and data[1]:
        return [{
            'id': msg['id'],
            'sender_id': msg['sender_id'],
            'receiver_id': msg['receiver_id'],
            'job_id': msg['job_id'],
            'content': msg['content'],
            'created_at': str(msg['created_at'])
        } for msg in data[1]]
    return []

def get_messages_for_job(job_id):
    supabase = get_db_connection()
    data, count = supabase.from_('messages').select('*').eq('job_id', job_id).order('created_at', desc=False).execute()
    if data and data[1]:
        return [{
            'id': msg['id'],
            'sender_id': msg['sender_id'],
            'receiver_id': msg['receiver_id'],
            'job_id': msg['job_id'],
            'content': msg['content'],
            'created_at': str(msg['created_at'])
        } for msg in data[1]]
    return []