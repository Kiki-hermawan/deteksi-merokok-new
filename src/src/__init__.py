import os
import queue
import threading
from flask import Flask
from twilio.rest import Client

# Import extensions before creating the app factory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
notification_queue = queue.Queue()

from .config import Config

def create_app(config_class=Config):
    """Creates and configures the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize Flask extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Import and register blueprints
    from .main.routes import main as main_blueprint
    from .auth.routes import auth as auth_blueprint
    from .api.routes import api_auth as api_auth_blueprint
    
    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(api_auth_blueprint)

    with app.app_context():
        # Create database tables if they don't exist
        db.create_all()

        # Start background threads only once, avoiding Flask reloader duplication
        if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            setup_background_tasks(app)

    return app

def setup_background_tasks(app):
    """Initializes and starts all background tasks."""
    from .camera.camera_manager import processor
    from .camera.camera_instance import detection_log_worker

    # Start the Twilio notification worker if configured
    if Config.TWILIO_ACCOUNT_SID and Config.TWILIO_AUTH_TOKEN:
        notif_thread = threading.Thread(target=notification_worker, daemon=True)
        notif_thread.start()
        print("Twilio notification worker started.")

    # Start the database logging worker
    db_log_thread = threading.Thread(target=detection_log_worker, args=(app,), daemon=True)
    db_log_thread.start()
    print("Database logging worker started.")

    # Pass the app context to the processor BEFORE setting up cameras
    processor.set_app(app)
    processor.setup_cameras_from_config()
    processor.start()

def notification_worker():
    """Background thread to send WhatsApp notifications."""
    client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
    while True:
        try:
            item = notification_queue.get()
            if item is None: break  # Sentinel for stopping
            camera_name, confidence = item
            message = client.messages.create(
                body=f"🚭 Smoking detected!\nCamera: {camera_name}\nConfidence: {confidence:.2f}",
                from_=Config.TWILIO_FROM_WHATSAPP,
                to=Config.TWILIO_TO_WHATSAPP
            )
            print(f"Notification sent: {message.sid}")
        except Exception as e:
            print(f"Notification worker error: {e}")