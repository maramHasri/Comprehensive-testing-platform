# from flask import Flask
# import socket
# from werkzeug.exceptions import HTTPException
# from flask_jwt_extended.exceptions import JWTDecodeError, NoAuthorizationError, InvalidHeaderError
# from jwt.exceptions import InvalidSubjectError, ExpiredSignatureError
# from app.extensions import db, migrate, jwt
# from app.config import Config
# from app.routes import api

# def test_connection() -> None:
#     smtp_host: str = "smtp.gmail.com"
#     smtp_port: int = 587
#     timeout_seconds: int = 10
#     try:
#         with socket.create_connection((smtp_host, smtp_port), timeout=timeout_seconds):
#             print(f"[startup] SMTP connectivity OK: {smtp_host}:{smtp_port}")
#     except OSError as err:
#         print(f"[startup] SMTP connectivity FAILED: {smtp_host}:{smtp_port} ({err})")
#     except Exception as err:
#         print(f"[startup] SMTP connectivity FAILED with unexpected error: {err}")

# def create_app():
    
#     app = Flask(__name__)
#     app.config.from_object(Config)
#     test_connection()

#     @app.get("/invite/<string:token>")
#     def invite_entry(token: str):
#         print(f"Invite link accessed: {token}")
#         return {
#             "message": "Invitation link is working",
#             "token": token,
#         }, 200

#     db.init_app(app)
#     migrate.init_app(app, db)
#     jwt.init_app(app)

#     # Reject tokens that are not stored (e.g. after logout) or expired in our session table
#     @jwt.token_in_blocklist_loader
#     def check_token_revoked(jwt_header, jwt_payload):
#         from app.models import UserSession
#         jti = jwt_payload.get("jti")
#         if not jti:
#             return True  # Old or invalid token shape
#         session = UserSession.query.filter_by(jti=jti).first()
#         if not session:
#             return True  # Token was revoked (logout) or never stored
#         if session.is_expired():
#             return True  # Session expired
#         return False  # Token is valid

#     # Normalize Authorization header: if token doesn't start with "Bearer ", add it
#     @app.before_request
#     def normalize_auth_header():
#         from flask import request
#         # Check if Authorization header exists and doesn't start with "Bearer "
#         auth_header = request.headers.get("Authorization", "")
#         if auth_header and not auth_header.startswith("Bearer "):
#             # Modify the WSGI environment to add "Bearer " prefix
#             # Flask reads headers from environ, so we modify that
#             request.environ["HTTP_AUTHORIZATION"] = f"Bearer {auth_header.strip()}"

#     # Handle JWT errors - Flask app level
#     @app.errorhandler(NoAuthorizationError)
#     def handle_no_auth(e):
#         return {"message": "Missing Authorization header. Enter your JWT token in the Authorization field."}, 401
    
#     @app.errorhandler(JWTDecodeError)
#     def handle_jwt_decode(e):
#         return {"message": "Invalid token format."}, 401
    
#     @app.errorhandler(InvalidHeaderError)
#     def handle_invalid_header(e):
#         return {"message": "Invalid token. Enter your JWT token in the Authorization field."}, 401
    
#     @app.errorhandler(InvalidSubjectError)
#     def handle_invalid_subject(e):
#         return {"message": "Invalid token format. Please login again to get a new token."}, 401

#     @app.errorhandler(ExpiredSignatureError)
#     def handle_expired_token(e):
#         return {"message": "Token has expired. Please login again to get a new token."}, 401

#     # Flask-JWT-Extended error handlers
#     @jwt.expired_token_loader
#     def expired_token_callback(jwt_header, jwt_payload):
#         return {"message": "Token has expired. Please login again."}, 401
    
#     @jwt.invalid_token_loader
#     def invalid_token_callback(error):
#         return {"message": f"Invalid token: {error}"}, 401
    
#     @jwt.unauthorized_loader
#     def missing_token_callback(error):
#         return {"message": "Missing Authorization header. Enter your JWT token in the Authorization field."}, 401

#     # Return JSON for 500 errors so clients see {"message": "...", "error": "..."} with real status 500
#     @app.errorhandler(500)
#     def handle_500(e):
#         description = getattr(e, "description", str(e))
#         if isinstance(e, HTTPException):
#             description = e.description or str(e)
#         return {"message": "An error occurred.", "error": description}, 500

#     # Swagger / API (namespaces registered in app.routes)
#     api.init_app(app)

#     # Register JWT error handlers with Flask-RESTx API
#     @api.errorhandler(NoAuthorizationError)
#     def handle_no_auth_api(e):
#         return {"message": "Missing Authorization header. Enter your JWT token in the Authorization field."}, 401
    
#     @api.errorhandler(JWTDecodeError)
#     def handle_jwt_decode_api(e):
#         return {"message": "Invalid token format."}, 401
    
#     @api.errorhandler(InvalidHeaderError)
#     def handle_invalid_header_api(e):
#         return {"message": "Invalid token. Enter your JWT token in the Authorization field."}, 401
    
#     @api.errorhandler(InvalidSubjectError)
#     def handle_invalid_subject_api(e):
#         return {"message": "Invalid token format. Please login again to get a new token."}, 401

#     @api.errorhandler(ExpiredSignatureError)
#     def handle_expired_token_api(e):
#         return {"message": "Token has expired. Please login again to get a new token."}, 401

#     return app


from flask import Flask
import socket
from werkzeug.exceptions import HTTPException
from flask_jwt_extended.exceptions import JWTDecodeError, NoAuthorizationError, InvalidHeaderError
from jwt.exceptions import InvalidSubjectError, ExpiredSignatureError

from app.extensions import db, migrate, jwt
from app.config import Config
from app.routes import api


def test_connection() -> None:
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    timeout_seconds: int = 10
    try:
        with socket.create_connection((smtp_host, smtp_port), timeout=timeout_seconds):
            print(f"[startup] SMTP connectivity OK: {smtp_host}:{smtp_port}")
    except OSError as err:
        print(f"[startup] SMTP connectivity FAILED: {smtp_host}:{smtp_port} ({err})")
    except Exception as err:
        print(f"[startup] SMTP connectivity FAILED with unexpected error: {err}")


def create_app():

    app = Flask(__name__)
    app.config.from_object(Config)

    test_connection()

    @app.get("/invite/<string:token>")
    def invite_entry(token: str):
        print(f"Invite link accessed: {token}")
        return {
            "message": "Invitation link is working",
            "token": token,
        }, 200

    # -----------------------
    # Extensions init
    # -----------------------
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # -----------------------
    # JWT blocklist check
    # -----------------------
    @jwt.token_in_blocklist_loader
    def check_token_revoked(jwt_header, jwt_payload):
        from app.models import UserSession
        jti = jwt_payload.get("jti")
        if not jti:
            return True
        session = UserSession.query.filter_by(jti=jti).first()
        if not session:
            return True
        if session.is_expired():
            return True
        return False

    # -----------------------
    # Auth header normalization
    # -----------------------
    @app.before_request
    def normalize_auth_header():
        from flask import request
        auth_header = request.headers.get("Authorization", "")
        if auth_header and not auth_header.startswith("Bearer "):
            request.environ["HTTP_AUTHORIZATION"] = f"Bearer {auth_header.strip()}"

    # -----------------------
    # App-level JWT errors
    # -----------------------
    @app.errorhandler(NoAuthorizationError)
    def handle_no_auth(e):
        return {"message": "Missing Authorization header. Enter your JWT token in the Authorization field."}, 401

    @app.errorhandler(JWTDecodeError)
    def handle_jwt_decode(e):
        return {"message": "Invalid token format."}, 401

    @app.errorhandler(InvalidHeaderError)
    def handle_invalid_header(e):
        return {"message": "Invalid token. Enter your JWT token in the Authorization field."}, 401

    @app.errorhandler(InvalidSubjectError)
    def handle_invalid_subject(e):
        return {"message": "Invalid token format. Please login again to get a new token."}, 401

    @app.errorhandler(ExpiredSignatureError)
    def handle_expired_token(e):
        return {"message": "Token has expired. Please login again to get a new token."}, 401

    # -----------------------
    # JWT extended handlers
    # -----------------------
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {"message": "Token has expired. Please login again."}, 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {"message": f"Invalid token: {error}"}, 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {"message": "Missing Authorization header. Enter your JWT token in the Authorization field."}, 401

    # -----------------------
    # 500 handler
    # -----------------------
    @app.errorhandler(500)
    def handle_500(e):
        description = getattr(e, "description", str(e))
        if isinstance(e, HTTPException):
            description = e.description or str(e)
        return {"message": "An error occurred.", "error": description}, 500

    # -----------------------
    # Swagger / API init
    # -----------------------
    api.init_app(app)

    # =====================================================
    # ✅ REGISTER NAMESPACES (THIS WAS MISSING)
    # =====================================================
    from app.routes.independent_teacher import independent_teachers_ns
    from app.routes.institution import educational_institutions_ns
    from app.routes.exams import exams_ns

    api.add_namespace(independent_teachers_ns, path="/teachers")
    api.add_namespace(educational_institutions_ns, path="/institutions")
    api.add_namespace(exams_ns, path="/exams")

    # -----------------------
    # API-level JWT errors
    # -----------------------
    @api.errorhandler(NoAuthorizationError)
    def handle_no_auth_api(e):
        return {"message": "Missing Authorization header. Enter your JWT token in the Authorization field."}, 401

    @api.errorhandler(JWTDecodeError)
    def handle_jwt_decode_api(e):
        return {"message": "Invalid token format."}, 401

    @api.errorhandler(InvalidHeaderError)
    def handle_invalid_header_api(e):
        return {"message": "Invalid token. Enter your JWT token in the Authorization field."}, 401

    @api.errorhandler(InvalidSubjectError)
    def handle_invalid_subject_api(e):
        return {"message": "Invalid token format. Please login again to get a new token."}, 401

    @api.errorhandler(ExpiredSignatureError)
    def handle_expired_token_api(e):
        return {"message": "Token has expired. Please login again to get a new token."}, 401

    return app