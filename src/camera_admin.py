import cv2
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required

from src import db
from src.models import Camera as CameraRecord
from src.camera.camera_manager import processor

camera_admin = Blueprint('camera_admin', __name__, url_prefix='/cameras')
SOURCE_TYPES = ('local', 'rtsp', 'http')


@camera_admin.route('/')
@login_required
def manage():
    cameras = CameraRecord.query.order_by(CameraRecord.id).all()
    return render_template('camera_manage.html', cameras=cameras)


@camera_admin.route('/add', methods=['POST'])
@login_required
def add():
    name = request.form.get('name', '').strip()
    source_type = request.form.get('source_type')
    source_value = request.form.get('source_value', '').strip()
    username = request.form.get('username') or None
    password = request.form.get('password') or None
    width = request.form.get('width', 1280, type=int)
    height = request.form.get('height', 720, type=int)
    fps = request.form.get('fps', 15, type=int)
    rtsp_transport = request.form.get('rtsp_transport', 'tcp')

    if not name or source_type not in SOURCE_TYPES or not source_value:
        flash('Nama, tipe sumber, dan alamat kamera wajib diisi.')
        return redirect(url_for('camera_admin.manage'))

    if source_type == 'local' and not source_value.isdigit():
        flash('Untuk webcam lokal, isi indeks perangkat (contoh: 0, 1).')
        return redirect(url_for('camera_admin.manage'))

    record = CameraRecord(
        name=name, source_type=source_type, source_value=source_value,
        username=username, password=password,
        width=width, height=height, fps=fps, rtsp_transport=rtsp_transport,
        is_active=True,
    )
    db.session.add(record)
    db.session.commit()

    processor.add_camera_runtime(record)

    flash(f'Kamera "{name}" berhasil ditambahkan.')
    return redirect(url_for('camera_admin.manage'))


@camera_admin.route('/<int:camera_id>/edit', methods=['POST'])
@login_required
def edit(camera_id):
    record = CameraRecord.query.get_or_404(camera_id)

    record.name = request.form.get('name', record.name).strip()
    record.source_type = request.form.get('source_type', record.source_type)
    record.source_value = request.form.get('source_value', record.source_value).strip()
    record.username = request.form.get('username') or None
    record.password = request.form.get('password') or None
    record.width = request.form.get('width', record.width, type=int)
    record.height = request.form.get('height', record.height, type=int)
    record.fps = request.form.get('fps', record.fps, type=int)
    record.rtsp_transport = request.form.get('rtsp_transport', record.rtsp_transport)
    db.session.commit()

    # Muat ulang kamera dengan konfigurasi terbaru
    processor.remove_camera(camera_id)
    processor.add_camera_runtime(record)

    flash(f'Kamera "{record.name}" berhasil diperbarui.')
    return redirect(url_for('camera_admin.manage'))


@camera_admin.route('/<int:camera_id>/delete', methods=['POST'])
@login_required
def delete(camera_id):
    record = CameraRecord.query.get_or_404(camera_id)
    processor.remove_camera(camera_id)
    db.session.delete(record)
    db.session.commit()
    flash(f'Kamera "{record.name}" telah dihapus.')
    return redirect(url_for('camera_admin.manage'))


@camera_admin.route('/<int:camera_id>/test', methods=['POST'])
@login_required
def test_connection(camera_id):
    record = CameraRecord.query.get_or_404(camera_id)
    source = record.build_source()
    try:
        if source.isdigit():
            cap = cv2.VideoCapture(int(source))
        elif source.startswith('rtsp'):
            cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
        else:
            cap = cv2.VideoCapture(source)

        # Batasi waktu tunggu supaya tidak menggantung server (butuh OpenCV >= 4.5.3)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 4000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 4000)

        ok = cap.isOpened()
        if ok:
            ret, _ = cap.read()
            ok = ok and ret
        cap.release()
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

    return jsonify({'success': ok})