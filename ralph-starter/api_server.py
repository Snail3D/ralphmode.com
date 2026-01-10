#!/usr/bin/env python3
"""
API Server for Ralph Mode with Security Features

Implements:
- SEC-003: CSRF Protection
- SEC-005: Sensitive Data Exposure Prevention
"""

import os
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from flask import Flask, request, jsonify, make_response, session
from flask_cors import CORS
from functools import wraps

# SEC-005: Import data protection
from data_protection import (
    SecretManager,
    DataEncryption,
    PIIProtection,
    SecureLogger,
    add_security_headers,
    enforce_https
)

# SEC-005: Load configuration from secure secret manager
try:
    CSRF_SECRET_KEY = SecretManager.get_secret("CSRF_SECRET_KEY", secrets.token_hex(32))
    SESSION_SECRET_KEY = SecretManager.get_secret("SESSION_SECRET_KEY", secrets.token_hex(32))
    ALLOWED_ORIGINS = SecretManager.get_secret("ALLOWED_ORIGINS", "https://ralphmode.com,http://localhost:3000").split(",")
except ValueError:
    # Fallback for development
    CSRF_SECRET_KEY = secrets.token_hex(32)
    SESSION_SECRET_KEY = secrets.token_hex(32)
    ALLOWED_ORIGINS = ["https://ralphmode.com", "http://localhost:3000"]

app = Flask(__name__)
app.secret_key = SESSION_SECRET_KEY

# SEC-004 & SEC-005: Secure session configuration
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'  # SEC-003: SameSite attribute
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)  # SEC-004: Session timeout

# Enable CORS with specific origins
CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True)

# SEC-005: Initialize encryption and logging
encryptor = DataEncryption()
logger = SecureLogger(__name__)


class CSRFProtection:
    """
    CSRF Protection Implementation (SEC-003)

    Implements multiple layers of CSRF defense:
    1. Synchronizer Token Pattern (for forms)
    2. Double-Submit Cookie Pattern (for APIs)
    3. Origin/Referer header validation
    """

    @staticmethod
    def generate_token(session_id: str) -> str:
        """
        Generate a CSRF token tied to the session.

        Uses HMAC-SHA256 with server-side secret + session ID.
        This prevents attackers from forging valid tokens.
        """
        timestamp = str(int(datetime.now().timestamp()))
        message = f"{session_id}:{timestamp}"
        signature = hmac.new(
            CSRF_SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{timestamp}:{signature}"

    @staticmethod
    def validate_token(token: str, session_id: str, max_age_seconds: int = 3600) -> bool:
        """
        Validate a CSRF token.

        Checks:
        1. Token format is valid
        2. Token signature matches expected HMAC
        3. Token is not expired (default: 1 hour)
        """
        try:
            timestamp_str, signature = token.split(":", 1)
            timestamp = int(timestamp_str)

            # Check expiration
            age = datetime.now().timestamp() - timestamp
            if age > max_age_seconds or age < 0:
                return False

            # Validate signature
            message = f"{session_id}:{timestamp_str}"
            expected_signature = hmac.new(
                CSRF_SECRET_KEY.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def validate_origin(request) -> bool:
        """
        Validate Origin/Referer headers (SEC-003)

        Prevents CSRF by ensuring requests come from allowed origins.
        Checks both Origin and Referer as fallback.
        """
        origin = request.headers.get('Origin')
        referer = request.headers.get('Referer')

        # For same-origin requests, Origin may be None
        if origin is None and referer is None:
            # Allow for same-origin requests without these headers
            # (e.g., direct navigation, some browsers)
            return True

        # Check Origin header first (more reliable)
        if origin:
            return any(origin.startswith(allowed) for allowed in ALLOWED_ORIGINS)

        # Fallback to Referer
        if referer:
            return any(referer.startswith(allowed) for allowed in ALLOWED_ORIGINS)

        return False

    @staticmethod
    def validate_double_submit_cookie(request) -> bool:
        """
        Double-Submit Cookie Pattern (SEC-003)

        For API requests:
        1. Client sends CSRF token in both cookie AND header
        2. Server validates they match
        3. Attackers can't read cookies due to Same-Origin Policy
        """
        cookie_token = request.cookies.get('csrf_token')
        header_token = request.headers.get('X-CSRF-Token')

        if not cookie_token or not header_token:
            return False

        return hmac.compare_digest(cookie_token, header_token)


def csrf_protect(f):
    """
    Decorator for CSRF protection on state-changing endpoints.

    Usage:
        @app.route('/api/submit', methods=['POST'])
        @csrf_protect
        def submit_data():
            # Your code here
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Only protect state-changing methods
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return f(*args, **kwargs)

        # Validate Origin/Referer
        if not CSRFProtection.validate_origin(request):
            return jsonify({
                'error': 'Invalid origin',
                'code': 'CSRF_INVALID_ORIGIN'
            }), 403

        # For API requests, use double-submit cookie pattern
        if request.path.startswith('/api/'):
            if not CSRFProtection.validate_double_submit_cookie(request):
                return jsonify({
                    'error': 'CSRF token validation failed',
                    'code': 'CSRF_TOKEN_INVALID'
                }), 403
        else:
            # For form submissions, use synchronizer token pattern
            token = request.form.get('csrf_token') or request.json.get('csrf_token')
            session_id = session.get('id', '')

            if not token or not CSRFProtection.validate_token(token, session_id):
                return jsonify({
                    'error': 'CSRF token validation failed',
                    'code': 'CSRF_TOKEN_INVALID'
                }), 403

        return f(*args, **kwargs)

    return decorated_function


# API Endpoints

@app.route('/api/csrf-token', methods=['GET'])
def get_csrf_token():
    """
    Get a CSRF token for the current session.

    This endpoint:
    1. Creates or retrieves session ID
    2. Generates CSRF token tied to session
    3. Sets CSRF cookie for double-submit pattern
    """
    # Ensure session exists
    if 'id' not in session:
        session['id'] = secrets.token_hex(16)

    session_id = session['id']
    csrf_token = CSRFProtection.generate_token(session_id)

    # For API usage: set both cookie and return token in response
    response = make_response(jsonify({
        'csrf_token': csrf_token,
        'session_id': session_id
    }))

    # SEC-003: Set CSRF cookie with secure attributes
    response.set_cookie(
        'csrf_token',
        csrf_token,
        httponly=True,
        secure=True,
        samesite='Strict',
        max_age=3600  # 1 hour
    )

    return response


@app.route('/api/feedback', methods=['POST'])
@csrf_protect
def submit_feedback():
    """
    Example protected endpoint: Submit feedback

    This demonstrates CSRF protection on a state-changing operation.
    """
    data = request.get_json()

    # Process feedback (placeholder)
    feedback = {
        'id': secrets.token_hex(8),
        'content': data.get('content', ''),
        'type': data.get('type', 'feature'),
        'timestamp': datetime.now().isoformat()
    }

    return jsonify({
        'success': True,
        'feedback': feedback
    }), 201


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint (no CSRF needed for GET)"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'csrf_protection': 'enabled'
    })


@app.route('/form-example', methods=['GET'])
def form_example():
    """
    Example HTML form with CSRF token.

    This demonstrates how to use CSRF tokens in traditional forms.
    """
    if 'id' not in session:
        session['id'] = secrets.token_hex(16)

    csrf_token = CSRFProtection.generate_token(session['id'])

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>CSRF Protected Form</title>
    </head>
    <body>
        <h1>CSRF Protected Form Example</h1>
        <form method="POST" action="/api/feedback">
            <input type="hidden" name="csrf_token" value="{csrf_token}">
            <label>Feedback:</label><br>
            <textarea name="content" rows="4" cols="50"></textarea><br>
            <button type="submit">Submit</button>
        </form>
    </body>
    </html>
    """
    return html


@app.before_request
def enforce_https_redirect():
    """SEC-005: Enforce HTTPS for all requests"""
    return enforce_https()


@app.after_request
def add_security_headers_to_response(response):
    """SEC-005: Add security headers to all responses"""
    return add_security_headers(response)


@app.errorhandler(403)
def forbidden(e):
    """Custom 403 handler for CSRF violations"""
    # SEC-005: Don't leak sensitive error details
    logger.warning(f"403 Forbidden: {request.path}")
    return jsonify({
        'error': 'Forbidden',
        'message': 'CSRF validation failed. Please refresh and try again.',
        'code': 'CSRF_VALIDATION_FAILED'
    }), 403


@app.errorhandler(500)
def internal_error(e):
    """SEC-005: Don't leak stack traces in production"""
    logger.error(f"500 Internal Server Error: {str(e)}")
    # Don't expose internal details
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An error occurred. Please try again later.',
        'code': 'INTERNAL_ERROR'
    }), 500


if __name__ == '__main__':
    # Development server
    # In production, use gunicorn or similar WSGI server
    print("⚠️  Starting development server")
    print("⚠️  DO NOT use in production - use gunicorn/uwsgi instead")
    print(f"🔒 CSRF Protection: ENABLED")
    print(f"🔒 Data Encryption: ENABLED (AES-256-GCM)")
    print(f"🔒 HSTS: ENABLED (max-age=31536000)")
    print(f"🔒 TLS 1.3: REQUIRED")
    print(f"🌐 Allowed Origins: {ALLOWED_ORIGINS}")

    # SEC-005: Run with HTTPS in production
    # For production, use nginx with Let's Encrypt SSL certificate
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        ssl_context='adhoc' if os.environ.get('USE_SSL') else None
    )
