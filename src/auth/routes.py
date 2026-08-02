import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import login_user, logout_user, login_required, current_user
import re

from src import db
from src.models import User

auth = Blueprint('auth', __name__)
ALLOWED_AVATAR_EXT = {'png', 'jpg', 'jpeg', 'webp'}

@auth.route('/login')
def login():
    return render_template('login.html', login_failed=False)

@auth.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')

    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password, password):
        flash('Nama pengguna atau kata sandi salah.')
        return render_template('login.html', login_failed=True, submitted_username=username)

    login_user(user)
    return redirect(url_for('main.index'))

@auth.route('/register')
def register():
    return render_template('register.html')

@auth.route('/register', methods=['POST'])
def register_post():
    username = request.form.get('username')
    password = request.form.get('password')
    password_confirm = request.form.get('password_confirm')

    # --- Start Validation ---
    if not username or not password or not password_confirm:
        flash('Username, password, dan konfirmasi password wajib diisi.')
        return redirect(url_for('auth.register'))

    if len(username) < 4:
        flash('Username must be at least 4 characters long.')
        return redirect(url_for('auth.register'))

    if not re.match(r'^\w+$', username):
        flash('Username can only contain letters, numbers, and underscores.')
        return redirect(url_for('auth.register'))

    if len(password) < 8:
        flash('Password must be at least 8 characters long.')
        return redirect(url_for('auth.register'))

    if password != password_confirm:
        flash('Password dan konfirmasi password tidak cocok.')
        return redirect(url_for('auth.register'))
    # --- End Validation ---

    user = User.query.filter_by(username=username).first()

    if user:
        flash('Username already exists. Please choose a different one.')
        return redirect(url_for('auth.register'))

    new_user = User(username=username, password=generate_password_hash(password, method='pbkdf2:sha256'))

    db.session.add(new_user)
    db.session.commit()

    flash('Registration successful. Please log in.')
    return redirect(url_for('auth.login'))

@auth.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)


@auth.route('/profile/avatar', methods=['POST'])
@login_required
def update_avatar():
    file = request.files.get('avatar')
    if not file or file.filename == '':
        flash('Pilih file foto terlebih dahulu.')
        return redirect(url_for('auth.profile'))

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_AVATAR_EXT:
        flash('Format foto harus png, jpg, jpeg, atau webp.')
        return redirect(url_for('auth.profile'))

    upload_dir = os.path.join(current_app.static_folder, 'avatars')
    os.makedirs(upload_dir, exist_ok=True)
    filename = secure_filename(f"user_{current_user.id}.{ext}")
    file.save(os.path.join(upload_dir, filename))

    current_user.avatar_filename = filename
    db.session.commit()
    flash('Foto profil berhasil diperbarui.')
    return redirect(url_for('auth.profile'))


@auth.route('/profile/password', methods=['POST'])
@login_required
def update_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not check_password_hash(current_user.password, current_password or ''):
        flash('Kata sandi saat ini salah.')
        return redirect(url_for('auth.profile'))

    if not new_password or len(new_password) < 8:
        flash('Kata sandi baru minimal 8 karakter.')
        return redirect(url_for('auth.profile'))

    if new_password != confirm_password:
        flash('Konfirmasi kata sandi baru tidak cocok.')
        return redirect(url_for('auth.profile'))

    current_user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
    db.session.commit()
    flash('Kata sandi berhasil diperbarui.')
    return redirect(url_for('auth.profile'))


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))