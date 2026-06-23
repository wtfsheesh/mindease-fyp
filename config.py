# Configuration settings for MindEase application

import os
from datetime import timedelta

class Config:
    """
    Configuration class for Flask application
    Contains all configuration variables from FYP report
    """
    
    # Basic Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
   # Database Configuration (SQLite 3.40 for development)
    # This automatically builds a perfect absolute path to mindease/instance/mindease.db
    _BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    _INSTANCE_DIR = os.path.join(_BASE_DIR, "instance")
    
    # Automatically make sure the instance folder exists
    if not os.path.exists(_INSTANCE_DIR):
        os.makedirs(_INSTANCE_DIR)
        
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f"sqlite:///{os.path.join(_INSTANCE_DIR, 'mindease.db')}"
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Google Gemini API Configuration
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    # Application Settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    
    RESPONSE_TIMEOUT = 2
    
    # Security Settings
    BCRYPT_LOG_ROUNDS = 12  # Password hashing rounds