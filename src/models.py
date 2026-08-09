import secrets
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

class DetectionLog(db.Model):
    __tablename__ = 'detection_logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    detail = db.Column(db.String(20), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    cam = db.Column(db.String(20))
    image_path = db.Column(db.String(255), nullable=True)
    image_filename = db.Column(db.String(255), nullable=True)

    def __init__(self, detail, confidence, cam, image_path=None, image_filename=None):
        self.detail = detail
        self.confidence = confidence
        self.cam = cam
        self.image_path = image_path
        self.image_filename = image_filename

    @property
    def has_image(self):
        return bool(self.image_path)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    avatar_filename = db.Column(db.String(255), nullable=True)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    otp_codes = db.relationship('EmailOTP', backref='user', lazy=True, cascade='all, delete-orphan')


class EmailOTP(db.Model):
    """Menyimpan kode OTP (One-Time Password) yang dikirim lewat email untuk verifikasi akun."""
    __tablename__ = 'email_otps'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    purpose = db.Column(db.String(20), nullable=False, default='register')  # 'register' (dapat diperluas: 'login', dll.)
    code_hash = db.Column(db.String(256), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    max_attempts = db.Column(db.Integer, default=5, nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_sent_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def generate_code(length=6):
        """Menghasilkan kode numerik acak yang aman secara kriptografis."""
        upper_bound = 10 ** length
        return str(secrets.randbelow(upper_bound)).zfill(length)

    def set_code(self, raw_code):
        self.code_hash = generate_password_hash(raw_code)

    def check_code(self, raw_code):
        return check_password_hash(self.code_hash, raw_code or '')

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at


class Camera(db.Model):
    __tablename__ = 'cameras'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    source_type = db.Column(db.String(20), nullable=False)   # 'local' | 'rtsp' | 'http'
    source_value = db.Column(db.String(255), nullable=False) # indeks device / URL
    username = db.Column(db.String(100), nullable=True)      # opsional, untuk RTSP berkredensial
    password = db.Column(db.String(100), nullable=True)
    width = db.Column(db.Integer, default=1280)
    height = db.Column(db.Integer, default=720)
    fps = db.Column(db.Integer, default=15)
    rtsp_transport = db.Column(db.String(10), default='tcp')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def build_source(self):
        """Bentuk string 'source' yang dipakai kelas Camera di camera_instance.py."""
        if self.source_type == 'local':
            return str(self.source_value)
        if self.source_type == 'rtsp' and self.username and self.password:
            if '://' in self.source_value:
                scheme, rest = self.source_value.split('://', 1)
                return f"{scheme}://{self.username}:{self.password}@{rest}"
        return self.source_value


class AlarmSetting(db.Model):
    __tablename__ = 'alarm_settings'
    id = db.Column(db.Integer, primary_key=True)
    sound_source = db.Column(db.String(20), default='preset')   # 'preset' | 'custom'
    sound_filename = db.Column(db.String(255), default='alarm.mp3')
    volume = db.Column(db.Float, default=1.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def sound_path(self):
        folder = 'uploads' if self.sound_source == 'custom' else 'presets'
        return f"audio/{folder}/{self.sound_filename}"

    @classmethod
    def get_current(cls):
        setting = cls.query.first()
        if not setting:
            setting = cls(sound_source='preset', sound_filename='alarm.mp3')
            db.session.add(setting)
            db.session.commit()
        return setting