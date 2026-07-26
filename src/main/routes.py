from flask import Blueprint, render_template, Response, send_file, abort, jsonify
from flask_login import login_required, current_user
import cv2
import time
import os
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.sql import text
from src.models import DetectionLog
from src.camera.camera_manager import processor

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def index():
    cameras_view = [
        {
            'name': cam.name,
            'running': cam.running,
        }
        for cam in processor.cameras
    ]
    return render_template('index.html', cameras=cameras_view, name=current_user.username)

@main.route('/detection_log')
@login_required
def detection_log():
    # Get all logs ordered by timestamp (newest first)
    logs = DetectionLog.query.order_by(DetectionLog.timestamp.desc()).limit(1000).all()
    
    return render_template('log.html', logs=logs)

@main.route('/analytics')
@login_required
def analytics():
    return render_template('analitycs.html')

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


@main.route('/api/detections/hourly')
@login_required
def api_detections_hourly():
    """
    Return detection count per hour for the last 24 hours.
    """
    try:
        from src import db
        
        now = datetime.now()
        hours_ago = now - timedelta(hours=24)
        
        # Use raw SQL for better MySQL compatibility
        query = text("""
        SELECT 
            HOUR(timestamp) as hour,
            DATE(timestamp) as date,
            COUNT(*) as count
        FROM detection_logs
        WHERE timestamp >= :hours_ago AND detail = 'merokok'
        GROUP BY DATE(timestamp), HOUR(timestamp)
        ORDER BY DATE(timestamp), HOUR(timestamp)
        """)
        
        result = db.session.execute(query, {"hours_ago": hours_ago})
        rows = result.fetchall()
        
        # Create 24-hour labels
        hourly_data = {}
        for i in range(24):
            hour_time = now - timedelta(hours=23-i)
            hour_label = hour_time.strftime('%H:00')
            hourly_data[hour_label] = 0
        
        # Fill in actual data
        for row in rows:
            hour = row[0]
            count = row[2]
            if hour is not None:
                hour_label = f"{int(hour):02d}:00"
                hourly_data[hour_label] = count
        
        return jsonify({
            'labels': list(hourly_data.keys()),
            'data': list(hourly_data.values())
        })
    except Exception as e:
        import traceback
        print(f"Error in api_detections_hourly: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@main.route('/api/detections/daily')
@login_required
def api_detections_daily():
    """
    Return detection count per day for the last 30 days.
    """
    try:
        from src import db
        
        now = datetime.now()
        days_ago = now - timedelta(days=30)
        
        # Use raw SQL for better MySQL compatibility
        query = text("""
        SELECT 
            DATE(timestamp) as day,
            COUNT(*) as count
        FROM detection_logs
        WHERE timestamp >= :days_ago AND detail = 'merokok'
        GROUP BY DATE(timestamp)
        ORDER BY DATE(timestamp)
        """)
        
        result = db.session.execute(query, {"days_ago": days_ago})
        rows = result.fetchall()
        
        # Create 30-day labels
        daily_data = {}
        for i in range(30):
            day_time = now - timedelta(days=29-i)
            day_label = day_time.strftime('%Y-%m-%d')
            daily_data[day_label] = 0
        
        # Fill in actual data
        for row in rows:
            day = row[0]
            count = row[1]
            if day:
                # day might be a datetime object or string
                if isinstance(day, str):
                    day_label = day
                else:
                    day_label = day.strftime('%Y-%m-%d')
                daily_data[day_label] = count
        
        return jsonify({
            'labels': list(daily_data.keys()),
            'data': list(daily_data.values())
        })
    except Exception as e:
        import traceback
        print(f"Error in api_detections_daily: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


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

@main.route('/camera/<int:camera_id>/toggle', methods=['POST'])
@login_required
def toggle_camera(camera_id):
    is_on = processor.toggle_camera(camera_id)
    if is_on is None:
        return jsonify({'error': 'Kamera tidak ditemukan'}), 404
    return jsonify({'camera_id': camera_id, 'running': is_on})