import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    DEBUG = os.getenv('FLASK_DEBUG', 'False') == 'True'
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', 5000))

    # MySQL configuration
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT')
    DB_NAME = os.getenv('DB_NAME')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 300,
        'pool_pre_ping': True
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Detection processor
    MODEL_PATH = os.getenv('MODEL_PATH', 'deteksi_merokok.pt')
    MIN_CONFIDENCE = float(os.getenv('MIN_CONFIDENCE', 0.5))
    MIN_LOG_INTERVAL = float(os.getenv('MIN_LOG_INTERVAL', 5))
    PROXIMITY_THRESHOLD = float(os.getenv('PROXIMITY_THRESHOLD', 0.3))

    # Multi-camera
    CAMERA_SOURCES = os.getenv('CAMERA_SOURCES', '0').split(',')
    CAMERA_NAMES = os.getenv('CAMERA_NAMES', 'Camera 1').split(',')
    CAMERA_WIDTHS = list(map(int, os.getenv('CAMERA_WIDTHS', '1280').split(',')))
    CAMERA_HEIGHTS = list(map(int, os.getenv('CAMERA_HEIGHTS', '720').split(',')))
    CAMERA_FPS = list(map(int, os.getenv('CAMERA_FPS', '30').split(',')))
    RTSP_TRANSPORT = os.getenv('RTSP_TRANSPORT', 'tcp')
    
    # Twilio Configuration
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_FROM_WHATSAPP = os.getenv('TWILIO_FROM_WHATSAPP')
    TWILIO_TO_WHATSAPP = os.getenv('TWILIO_TO_WHATSAPP')

    # Email / SMTP configuration (dipakai untuk mengirim OTP verifikasi akun)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', MAIL_USERNAME)

    # OTP configuration
    OTP_LENGTH = int(os.getenv('OTP_LENGTH', 6))
    OTP_EXPIRE_MINUTES = int(os.getenv('OTP_EXPIRE_MINUTES', 5))
    OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv('OTP_RESEND_COOLDOWN_SECONDS', 60))