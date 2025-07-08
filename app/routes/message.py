from flask import Blueprint, request, jsonify
from app.services.message_services import create_message, get_messages_between_users, get_messages_for_job
from app.utils.auth_utils import verify_supabase_token, get_current_user_id

message_bp = Blueprint('message', __name__)

@message_bp.route('/messages', methods=['POST'])
def add_message():
    try:
        data = request.json
        sender_id = data.get('sender_id')
        receiver_id = data.get('receiver_id')
        job_id = data.get('job_id')
        content = data.get('content')

        if not all([sender_id, receiver_id, content]):
            return jsonify({'error': 'Missing required fields'}), 400

        message_id = create_message(sender_id, receiver_id, job_id, content)
        return jsonify({'message': 'Message sent successfully', 'message_id': message_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/messages/between/<uuid:user1_id>/<uuid:user2_id>', methods=['GET'])
def retrieve_messages_between_users(user1_id, user2_id):
    try:
        messages = get_messages_between_users(str(user1_id), str(user2_id))
        return jsonify(messages), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/messages/job/<uuid:job_id>', methods=['GET'])
def retrieve_messages_for_job(job_id):
    try:
        messages = get_messages_for_job(str(job_id))
        return jsonify(messages), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500