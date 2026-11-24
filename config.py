import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
    ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH')
    AI_API_KEY = os.environ.get('AI_API_KEY')
    AI_API_BASE_URL = os.environ.get('AI_API_BASE_URL', 'https://api.openai.com/v1')
    AI_MODEL = os.environ.get('AI_MODEL', 'gpt-4o-mini')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///campusconnect.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
