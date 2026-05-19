from flask import Flask, g, request
from flask_session import Session
from config import Config
from extensions import db, login_manager
import time
import traceback
import cloudwatch_logger as cw

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(user_id)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access your vault.'
    login_manager.login_message_category = 'info'

    Session(app)

    @app.before_request
    def start_timer():
        g.start_time = time.time()

    @app.after_request
    def log_request_performance(response):
        if hasattr(g, 'start_time'):
            duration_ms = (time.time() - g.start_time) * 1000
            if request.path and not request.path.startswith('/static'):
                cw.log_performance(request.endpoint or request.path, request.method, duration_ms)
        return response

    @app.errorhandler(Exception)
    def handle_unhandled_exception(e):
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return e
            
        tb = traceback.format_exc()
        cw.log_error(f"Unhandled Exception: {str(e)}", {'path': request.path, 'traceback': tb})
        return "Internal Server Error. The issue has been logged.", 500

    with app.app_context():
        from models import User, OTPRecord, NoteMetadata
        from auth import auth_bp
        from notes import notes_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(notes_bp)
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)