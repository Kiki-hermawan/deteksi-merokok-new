from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
import re

from src import db
from src.models import User

auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    
    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password, password):
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login'))

    login_user(user)
    return redirect(url_for('main.index'))

@auth.route('/register')
def register():
    return render_template('register.html')

@auth.route('/register', methods=['POST'])
def register_post():
    username = request.form.get('username')
    password = request.form.get('password')

    # --- Start Validation ---
    if not username or not password:
        flash('Username and password are required.')
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
    # The @login_required decorator ensures that current_user is a logged-in user.
    # Flask-Login automatically uses your load_user function to get this object.
    return render_template('profile.html', user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))