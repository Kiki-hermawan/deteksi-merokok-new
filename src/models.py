from flask_login import UserMixin
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
    password = db.Column(db.String(256), nullable=False)