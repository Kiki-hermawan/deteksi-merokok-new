from flask_login import UserMixin
from . import db

class DetectionLog(db.Model):
    __tablename__ = 'detection_logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    detail = db.Column(db.String(20), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    cam = db.Column(db.String(20))

    def __init__(self, detail, confidence, cam):
        self.detail = detail
        self.confidence = confidence
        self.cam = cam

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)