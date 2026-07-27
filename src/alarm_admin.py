import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename

from src import db
from src.models import AlarmSetting

alarm_admin = Blueprint('alarm_admin', __name__, url_prefix='/alarm')
ALLOWED_EXT = {'mp3', 'wav', 'ogg'}


def _presets_dir():
    return os.path.join(current_app.static_folder, 'audio', 'presets')


def _uploads_dir():
    path = os.path.join(current_app.static_folder, 'audio', 'uploads')
    os.makedirs(path, exist_ok=True)
    return path


@alarm_admin.route('/')
@login_required
def manage():
    setting = AlarmSetting.get_current()
    presets_dir = _presets_dir()
    presets = sorted(os.listdir(presets_dir)) if os.path.isdir(presets_dir) else []
    return render_template('alarm_manage.html', setting=setting, presets=presets)


@alarm_admin.route('/select-preset', methods=['POST'])
@login_required
def select_preset():
    filename = request.form.get('preset_filename')
    if not filename or not os.path.isfile(os.path.join(_presets_dir(), filename)):
        flash('Preset suara tidak ditemukan.')
        return redirect(url_for('alarm_admin.manage'))

    setting = AlarmSetting.get_current()
    setting.sound_source = 'preset'
    setting.sound_filename = filename
    db.session.commit()
    flash('Suara alarm diperbarui menjadi preset.')
    return redirect(url_for('alarm_admin.manage'))


@alarm_admin.route('/upload', methods=['POST'])
@login_required
def upload_custom():
    file = request.files.get('sound_file')
    if not file or file.filename == '':
        flash('Pilih file suara terlebih dahulu.')
        return redirect(url_for('alarm_admin.manage'))

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_EXT:
        flash('Format file harus mp3, wav, atau ogg.')
        return redirect(url_for('alarm_admin.manage'))

    filename = secure_filename(file.filename)
    file.save(os.path.join(_uploads_dir(), filename))

    setting = AlarmSetting.get_current()
    setting.sound_source = 'custom'
    setting.sound_filename = filename
    db.session.commit()
    flash('Suara alarm kustom berhasil diunggah dan diaktifkan.')
    return redirect(url_for('alarm_admin.manage'))


@alarm_admin.route('/volume', methods=['POST'])
@login_required
def set_volume():
    volume = request.form.get('volume', 1.0, type=float)
    volume = max(0.0, min(1.0, volume))
    setting = AlarmSetting.get_current()
    setting.volume = volume
    db.session.commit()
    flash('Volume alarm diperbarui.')
    return redirect(url_for('alarm_admin.manage'))