from flask import Blueprint, render_template, Response, send_file, abort
from flask_login import login_required, current_user
import cv2
import time
import os
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

@main.route('/detection_log_image/<int:log_id>')
@login_required
def detection_log_image(log_id):
    """Serve the captured detection image inline (for preview)."""
    log = DetectionLog.query.get_or_404(log_id)
    if not log.image_path or not os.path.isfile(log.image_path):
        abort(404)
    return send_file(log.image_path, mimetype='image/jpeg')

@main.route('/detection_log_image/<int:log_id>/download')
@login_required
def detection_log_image_download(log_id):
    """Serve the captured detection image as a download."""
    log = DetectionLog.query.get_or_404(log_id)
    if not log.image_path or not os.path.isfile(log.image_path):
        abort(404)
    download_name = log.image_filename or f"detection_{log_id}.jpg"
    return send_file(
        log.image_path,
        mimetype='image/jpeg',
        as_attachment=True,
        download_name=download_name
    )

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