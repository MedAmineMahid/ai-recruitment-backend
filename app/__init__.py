from flask import Flask
from supabase import create_client

from dotenv import load_dotenv
from flask import request
from flask_cors import CORS
from flask import Flask, send_from_directory, jsonify, current_app

# === SkillNer Setup ===
import spacy
from spacy.matcher import PhraseMatcher
from skillNer.general_params import SKILL_DB
from skillNer.skill_extractor_class import SkillExtractor

load_dotenv()

import os

def create_app():
    app = Flask(__name__)

    import logging
    logging.basicConfig(level=logging.INFO)

    @app.before_request
    def log_request_headers():
        current_app.logger.info(f"Incoming Request Headers: {request.headers}")

    # Supabase configuration
    app.supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

    # Configure upload folder for local CV storage
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads', 'cvs')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.logger.info(f"UPLOAD_FOLDER configured at: {app.config['UPLOAD_FOLDER']}")

    # Database configuration
    app.config['DB_HOST'] = os.getenv('DB_HOST')
    app.config['DB_NAME'] = os.getenv('DB_NAME')
    app.config['DB_USER'] = os.getenv('DB_USER')
    app.config['DB_PASSWORD'] = os.getenv('DB_PASSWORD')

    # Serve static files from the uploads/cvs directory
    app.add_url_rule('/uploads/cvs/<path:filename>',
                     endpoint='uploaded_cvs',
                     view_func=lambda filename: send_from_directory(app.config['UPLOAD_FOLDER'], filename))

    # === Initialize SkillNer once ===
    nlp = spacy.load("en_core_web_lg")
    app.skill_extractor = SkillExtractor(nlp, SKILL_DB, PhraseMatcher)
    app.SKILL_DB=SKILL_DB
    CORS(app, origins=os.getenv('CORS_ORIGINS', 'http://localhost:3000'), supports_credentials=True)

    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.cv import cv_bp
    from .routes.profile import profile_bp
    from .routes.job import job_bp
    from .routes.parser import parser_bp
    
    from .routes.message import message_bp
    from .routes.dashboard import dashboard_bp
    from .routes.application import application_bp
    from .routes.ai_matching_routes import ai_matching_bp
    from .routes.company import company_bp


    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(cv_bp, url_prefix="/cv")
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(parser_bp, url_prefix="/parser")
    
    app.register_blueprint(message_bp, url_prefix="/message")
    app.register_blueprint(job_bp, url_prefix="/job")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(application_bp, url_prefix="/application")
    app.register_blueprint(ai_matching_bp)
    app.register_blueprint(company_bp, url_prefix="/company")

    @app.route("/", methods=["GET", "OPTIONS"])
    def root():
        return jsonify({"status": "OK"}), 200


    return app
