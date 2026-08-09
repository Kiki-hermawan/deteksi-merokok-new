import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import login_user, logout_user, login_required, current_user
import re

from src import db
from src.models import User, EmailOTP
from src.mailer import send_otp_email, send_reset_password_email
from src.tokens import generate_reset_token, verify_reset_token

auth = Blueprint('auth', __name__)
ALLOWED_AVATAR_EXT = {'png', 'jpg', 'jpeg', 'webp'}
EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
OTP_PURPOSE_REGISTER = 'register'

# Kata sandi wajib: minimal 8 karakter, mengandung huruf besar, huruf kecil,
# angka, dan simbol. Dicek lewat fungsi (bukan satu regex besar) supaya
# pesan error bisa lebih spesifik menunjukkan syarat mana yang belum terpenuhi.
PASSWORD_MIN_LENGTH = 8
PASSWORD_SPECIAL_CHARS = r"""!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?"""


def validate_password_strength(password):
    """Mengembalikan (is_valid, pesan_error) untuk aturan kekuatan kata sandi."""
    if not password or len(password) < PASSWORD_MIN_LENGTH:
        return False, f'Kata sandi minimal {PASSWORD_MIN_LENGTH} karakter.'
    if not re.search(r'[a-z]', password):
        return False, 'Kata sandi harus mengandung minimal satu huruf kecil.'
    if not re.search(r'[A-Z]', password):
        return False, 'Kata sandi harus mengandung minimal satu huruf besar.'
    if not re.search(r'\d', password):
        return False, 'Kata sandi harus mengandung minimal satu angka.'
    if not re.search(f'[{PASSWORD_SPECIAL_CHARS}]', password):
        return False, 'Kata sandi harus mengandung minimal satu simbol (mis. ! @ # $ %).'
    return True, ''


def _issue_and_send_otp(user, purpose=OTP_PURPOSE_REGISTER):
    """Membuat kode OTP baru untuk user, menyimpannya (ter-hash), lalu mengirimkannya lewat email."""
    code = EmailOTP.generate_code(length=current_app.config['OTP_LENGTH'])
    otp = EmailOTP(
        user_id=user.id,
        purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=current_app.config['OTP_EXPIRE_MINUTES']),
        last_sent_at=datetime.utcnow(),
    )
    otp.set_code(code)
    db.session.add(otp)
    db.session.commit()

    send_otp_email(user.email, user.username, code, current_app.config['OTP_EXPIRE_MINUTES'])
    return otp


def _ensure_active_otp(user, purpose=OTP_PURPOSE_REGISTER):
    """Mengembalikan OTP aktif (belum dipakai & belum kedaluwarsa) jika ada, atau membuat yang baru."""
    active = (
        EmailOTP.query
        .filter_by(user_id=user.id, purpose=purpose, is_used=False)
        .order_by(EmailOTP.created_at.desc())
        .first()
    )
    if active and not active.is_expired:
        return active
    return _issue_and_send_otp(user, purpose=purpose)


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

    if not user.is_verified:
        _ensure_active_otp(user, purpose=OTP_PURPOSE_REGISTER)
        session['pending_verification_user_id'] = user.id
        flash('Akun Anda belum diverifikasi. Kami telah mengirim kode OTP ke email Anda, silakan verifikasi terlebih dahulu.')
        return redirect(url_for('auth.verify_otp'))

    login_user(user)
    return redirect(url_for('main.index'))

@auth.route('/register')
def register():
    return render_template('register.html')

@auth.route('/register', methods=['POST'])
def register_post():
    username = request.form.get('username')
    email = (request.form.get('email') or '').strip().lower()
    phone = request.form.get('phone', '').strip()
    password = request.form.get('password')
    password_confirm = request.form.get('password_confirm')

    # --- Start Validation ---
    if not username or not email or not password or not password_confirm:
        flash('Username, email, password, dan konfirmasi password wajib diisi.')
        return redirect(url_for('auth.register'))

    if len(username) < 4:
        flash('Username must be at least 4 characters long.')
        return redirect(url_for('auth.register'))

    if not re.match(r'^\w+$', username):
        flash('Username can only contain letters, numbers, and underscores.')
        return redirect(url_for('auth.register'))

    if not EMAIL_REGEX.match(email):
        flash('Format email tidak valid.')
        return redirect(url_for('auth.register'))
    
    if not re.match(r'^(\+62|62|0)8[1-9][0-9]{6,10}$', phone):
            flash('Format nomor HP tidak valid.')
            return redirect(url_for('auth.register'))

    if User.query.filter_by(phone=phone).first():
            flash('Nomor HP sudah terdaftar.')
            return redirect(url_for('auth.register'))

    password_valid, password_error = validate_password_strength(password)
    if not password_valid:
        flash(password_error)
        return redirect(url_for('auth.register'))

    if password != password_confirm:
        flash('Password dan konfirmasi password tidak cocok.')
        return redirect(url_for('auth.register'))
    # --- End Validation ---

    if User.query.filter_by(username=username).first():
        flash('Username already exists. Please choose a different one.')
        return redirect(url_for('auth.register'))

    if User.query.filter_by(email=email).first():
        flash('Email sudah terdaftar. Gunakan email lain atau masuk ke akun Anda.')
        return redirect(url_for('auth.register'))

    new_user = User(
        username=username,
        email=email,
        phone=phone,
        password=generate_password_hash(password, method='pbkdf2:sha256'),
        is_verified=False,
    )

    db.session.add(new_user)
    db.session.commit()

    try:
        _issue_and_send_otp(new_user, purpose=OTP_PURPOSE_REGISTER)
    except Exception:
        current_app.logger.exception('Gagal mengirim email OTP saat registrasi user_id=%s', new_user.id)
        flash('Registrasi berhasil, tetapi pengiriman email OTP gagal. Silakan minta kirim ulang kode OTP.')

    session['pending_verification_user_id'] = new_user.id
    flash(f'Kode OTP telah dikirim ke {email}. Masukkan kode tersebut untuk mengaktifkan akun Anda.')
    return redirect(url_for('auth.verify_otp'))


@auth.route('/verify-otp')
def verify_otp():
    user_id = session.get('pending_verification_user_id')
    if not user_id:
        flash('Tidak ada proses verifikasi yang aktif. Silakan daftar atau masuk terlebih dahulu.')
        return redirect(url_for('auth.register'))

    user = User.query.get(user_id)
    if not user or user.is_verified:
        session.pop('pending_verification_user_id', None)
        return redirect(url_for('auth.login'))

    return render_template('verify_otp.html', email=user.email)


@auth.route('/verify-otp', methods=['POST'])
def verify_otp_post():
    user_id = session.get('pending_verification_user_id')
    code = (request.form.get('otp_code') or '').strip()

    if not user_id:
        flash('Sesi verifikasi telah berakhir. Silakan daftar kembali.')
        return redirect(url_for('auth.register'))

    user = User.query.get(user_id)
    if not user:
        session.pop('pending_verification_user_id', None)
        flash('Akun tidak ditemukan.')
        return redirect(url_for('auth.register'))

    if user.is_verified:
        session.pop('pending_verification_user_id', None)
        flash('Akun sudah terverifikasi. Silakan masuk.')
        return redirect(url_for('auth.login'))

    if not code:
        flash('Kode OTP wajib diisi.')
        return redirect(url_for('auth.verify_otp'))

    otp = (
        EmailOTP.query
        .filter_by(user_id=user.id, purpose=OTP_PURPOSE_REGISTER, is_used=False)
        .order_by(EmailOTP.created_at.desc())
        .first()
    )

    if not otp:
        flash('Kode OTP tidak ditemukan. Silakan minta kode baru.')
        return redirect(url_for('auth.verify_otp'))

    if otp.is_expired:
        flash('Kode OTP telah kedaluwarsa. Silakan minta kode baru.')
        return redirect(url_for('auth.verify_otp'))

    if otp.attempts >= otp.max_attempts:
        flash('Terlalu banyak percobaan yang salah. Silakan minta kode baru.')
        return redirect(url_for('auth.verify_otp'))

    if not otp.check_code(code):
        otp.attempts += 1
        db.session.commit()
        sisa = max(otp.max_attempts - otp.attempts, 0)
        flash(f'Kode OTP salah. Sisa percobaan: {sisa}.')
        return redirect(url_for('auth.verify_otp'))

    otp.is_used = True
    user.is_verified = True
    db.session.commit()
    session.pop('pending_verification_user_id', None)

    flash('Verifikasi berhasil. Akun Anda sudah aktif, silakan masuk.')
    return redirect(url_for('auth.login'))


@auth.route('/verify-otp/resend', methods=['POST'])
def resend_otp():
    user_id = session.get('pending_verification_user_id')
    if not user_id:
        flash('Sesi verifikasi telah berakhir. Silakan daftar kembali.')
        return redirect(url_for('auth.register'))

    user = User.query.get(user_id)
    if not user or user.is_verified:
        session.pop('pending_verification_user_id', None)
        return redirect(url_for('auth.login'))

    last_otp = (
        EmailOTP.query
        .filter_by(user_id=user.id, purpose=OTP_PURPOSE_REGISTER)
        .order_by(EmailOTP.created_at.desc())
        .first()
    )

    cooldown = current_app.config['OTP_RESEND_COOLDOWN_SECONDS']
    if last_otp:
        elapsed = (datetime.utcnow() - last_otp.last_sent_at).total_seconds()
        if elapsed < cooldown:
            sisa = int(cooldown - elapsed)
            flash(f'Mohon tunggu {sisa} detik sebelum meminta kode baru.')
            return redirect(url_for('auth.verify_otp'))

    try:
        _issue_and_send_otp(user, purpose=OTP_PURPOSE_REGISTER)
        flash(f'Kode OTP baru telah dikirim ke {user.email}.')
    except Exception:
        current_app.logger.exception('Gagal mengirim ulang email OTP user_id=%s', user.id)
        flash('Gagal mengirim ulang kode OTP. Silakan coba lagi beberapa saat lagi.')

    return redirect(url_for('auth.verify_otp'))


@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        generic_message = (
            'Jika email terdaftar di sistem kami, link reset kata sandi telah dikirim. '
            'Silakan cek email Anda (termasuk folder spam).'
        )

        if not email:
            flash('Email wajib diisi.')
            return redirect(url_for('auth.forgot_password'))

        user = User.query.filter_by(email=email).first()
        if user:
            token = generate_reset_token(user.id)
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            try:
                send_reset_password_email(
                    user.email,
                    user.username,
                    reset_url,
                    current_app.config['RESET_PASSWORD_EXPIRE_MINUTES'],
                )
            except Exception:
                current_app.logger.exception('Gagal mengirim email reset password user_id=%s', user.id)

        # Pesan yang sama ditampilkan baik email terdaftar maupun tidak,
        # supaya tidak bisa dipakai untuk menebak email mana yang punya akun.
        flash(generic_message)
        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')


@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    max_age_seconds = current_app.config['RESET_PASSWORD_EXPIRE_MINUTES'] * 60
    user_id = verify_reset_token(token, max_age_seconds=max_age_seconds)

    if not user_id:
        flash('Link reset kata sandi tidak valid atau sudah kedaluwarsa. Silakan minta link baru.')
        return redirect(url_for('auth.forgot_password'))

    user = User.query.get(user_id)
    if not user:
        flash('Akun tidak ditemukan.')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        password_valid, password_error = validate_password_strength(new_password)
        if not password_valid:
            flash(password_error)
            return redirect(url_for('auth.reset_password', token=token))

        if new_password != confirm_password:
            flash('Konfirmasi kata sandi tidak cocok.')
            return redirect(url_for('auth.reset_password', token=token))

        user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
        db.session.commit()

        flash('Kata sandi berhasil direset. Silakan masuk dengan kata sandi baru Anda.')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', token=token)


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

    password_valid, password_error = validate_password_strength(new_password)
    if not password_valid:
        flash(password_error)
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