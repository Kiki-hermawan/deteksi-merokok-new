from flask import Blueprint, render_template, Response
from flask_login import login_required, current_user
import cv2
import time
from src.models import DetectionLog
from src.camera.camera_manager import processor

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def index():
    return render_template('index.html', cameras=processor.cameras, name=current_user.username)

@main.route('/detection_log')
@login_required
def detection_log():
    logs = DetectionLog.query.order_by(DetectionLog.timestamp.desc()).limit(50).all()
    return render_template('log.html', logs=logs)

@main.route('/video_feed/<int:camera_id>')
@login_required
def video_feed(camera_id):
    def generate(camera_id):
        camera = processor.get_camera(camera_id)
        while True:
            frame = camera.get_latest_frame()
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame)
                if not ret:
                    continue
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.05)
    return Response(generate(camera_id), mimetype='multipart/x-mixed-replace; boundary=frame')