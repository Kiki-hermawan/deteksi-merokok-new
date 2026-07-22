from flask import Blueprint, render_template, Response, send_file, abort, jsonify
from flask_login import login_required, current_user
import cv2
import time
import os
from sqlalchemy import func
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

@main.route('/api/stats')
@login_required
def api_stats():
    """
    Return aggregated detection statistics for the dashboard charts.
    - detection_status: total detected vs not detected (not detected is
      currently 0 because the system only logs positive 'merokok' events).
    - camera_breakdown: count and percentage per camera.
    - avg_confidence: average confidence across all logs.
    """
    total_detected = DetectionLog.query.filter_by(detail='merokok').count()
    avg_confidence = (
        DetectionLog.query.with_entities(func.avg(DetectionLog.confidence))
        .filter_by(detail='merokok')
        .scalar()
    ) or 0.0

    rows = (
        DetectionLog.query
        .with_entities(DetectionLog.cam, func.count(DetectionLog.id).label('count'))
        .filter_by(detail='merokok')
        .group_by(DetectionLog.cam)
        .all()
    )

    camera_breakdown = []
    for cam, count in rows:
        pct = round((count / total_detected) * 100, 1) if total_detected else 0.0
        camera_breakdown.append({
            'name': cam or 'Unknown',
            'count': count,
            'percentage': pct
        })

    return jsonify({
        'detection_status': {
            'detected': total_detected,
            'not_detected': 0
        },
        'camera_breakdown': camera_breakdown,
        'avg_confidence': float(avg_confidence)
    })


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