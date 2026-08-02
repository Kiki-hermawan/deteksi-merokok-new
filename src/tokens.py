"""Utility untuk membuat & memverifikasi token reset password yang aman dan punya masa berlaku."""
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app

RESET_PASSWORD_SALT = 'reset-password'


def generate_reset_token(user_id):
    """Membuat token reset password yang berisi user_id, ditandatangani dengan SECRET_KEY."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps({'user_id': user_id}, salt=RESET_PASSWORD_SALT)


def verify_reset_token(token, max_age_seconds=1800):
    """Memverifikasi token reset password.

    Mengembalikan user_id jika token valid & belum kedaluwarsa, atau None jika
    tidak valid / rusak / sudah kedaluwarsa.
    """
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = serializer.loads(token, salt=RESET_PASSWORD_SALT, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
    return data.get('user_id')
