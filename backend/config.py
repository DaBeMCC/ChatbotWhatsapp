import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_NAME = os.getenv('DB_NAME', 'chatbot_whatsapp')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')

    WHATSAPP_SERVICE_URL = os.getenv('WHATSAPP_SERVICE_URL', 'http://localhost:3000')
    INTERNAL_API_KEY = os.getenv('INTERNAL_API_KEY', '')

    OTP_EXPIRY_MINUTES = int(os.getenv('OTP_EXPIRY_MINUTES', 5))
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-change-in-production')
