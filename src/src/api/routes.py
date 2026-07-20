import jwt
import datetime
from functools import wraps
from flask import request, jsonify, Blueprint, current_app
from werkzeug.security import check_password_hash

from src.models import User
from src import db

api_auth = Blueprint('api_auth', __name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            parts = auth_header.split()
            # Expected header format: "Bearer <token>"
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(id=data['user_id']).first()
            if not current_user:
                 return jsonify({'message': 'Token is invalid!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401

        return f(current_user, *args, **kwargs)
    return decorated

@api_auth.route('/api/login', methods=['POST'])
def api_login():
    """API login endpoint. Takes username/password and returns a JWT."""
    auth_data = request.json
    if not auth_data or not auth_data.get('username') or not auth_data.get('password'):
        return jsonify({'message': 'Could not verify'}), 401

    user = User.query.filter_by(username=auth_data.get('username')).first()

    if not user or not check_password_hash(user.password, auth_data.get('password')):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    # Generate the token
    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    }, current_app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({'token': token})

@api_auth.route('/api/protected')
@token_required
def protected_api_route(current_user):
    """An example of a protected API route."""
    return jsonify({'message': f'This is a protected route. Welcome {current_user.username}!'})