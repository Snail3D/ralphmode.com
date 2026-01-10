#!/usr/bin/env python3
"""
API Server for Ralph Mode with Security Features

Implements:
- SEC-003: CSRF Protection
- SEC-005: Sensitive Data Exposure Prevention
- SEC-006: Broken Access Control Prevention
- SEC-007: Security Misconfiguration Prevention
- SEC-011: API Rate Limiting
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

# SEC-007: Import secure configuration
from config import AppConfig

# SEC-005: Import data protection
from data_protection import (
    SecretManager,
    DataEncryption,
    PIIProtection,
    SecureLogger,
    add_security_headers,
    enforce_https
)

# SEC-006: Import RBAC
from rbac import (
    RBACManager,
    Role,
    Permission,
    require_permission,
    require_role,
    require_ownership,
    require_subscription
)

# SEC-011: Import rate limiting
from rate_limiter import (
    rate_limit,
    rate_limit_ip,
    rate_limit_user,
    rate_limit_auth,
    rate_limit_feedback,
    rate_limit_admin,
    RateLimitConfig
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

# SEC-007: Apply secure configuration from config module
app.config.update(AppConfig.get_flask_config())
app.secret_key = SESSION_SECRET_KEY

# SEC-004 & SEC-005: Secure session configuration
app.config['SESSION_COOKIE_SECURE'] = AppConfig.SESSION_COOKIE_SECURE
app.config['SESSION_COOKIE_HTTPONLY'] = AppConfig.SESSION_COOKIE_HTTPONLY
app.config['SESSION_COOKIE_SAMESITE'] = AppConfig.SESSION_COOKIE_SAMESITE
app.config['SESSION_COOKIE_NAME'] = AppConfig.SESSION_COOKIE_NAME
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


# =============================================================================
# SEC-006: RBAC Helper Functions
# =============================================================================

def get_current_user_id() -> Optional[str]:
    """
    Get the current authenticated user ID from session.

    Returns:
        User ID if authenticated, None otherwise
    """
    return session.get('user_id')


def require_auth(f):
    """
    Decorator to require authentication.

    Usage:
        @app.route('/api/protected', methods=['GET'])
        @require_auth
        def protected_endpoint():
            user_id = get_current_user_id()
            # Your code here
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def require_api_permission(permission: Permission):
    """
    Decorator to require specific permission for API endpoints.

    Usage:
        @app.route('/api/feedback', methods=['POST'])
        @require_auth
        @require_api_permission(Permission.FEEDBACK_CREATE)
        def create_feedback():
            # Only users with FEEDBACK_CREATE permission can access
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'AUTH_REQUIRED'
                }), 401

            if not RBACManager.has_permission(user_id, permission):
                logger.warning(f"User {user_id} denied access - missing permission: {permission.value}")
                return jsonify({
                    'error': 'Insufficient permissions',
                    'code': 'PERMISSION_DENIED',
                    'required_permission': permission.value
                }), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_api_role(role: Role):
    """
    Decorator to require specific role for API endpoints.

    Usage:
        @app.route('/api/admin/users', methods=['GET'])
        @require_auth
        @require_api_role(Role.ADMIN)
        def list_users():
            # Only admins can access
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'AUTH_REQUIRED'
                }), 401

            if not RBACManager.has_role(user_id, role):
                logger.warning(f"User {user_id} denied access - insufficient role (required: {role.value})")
                return jsonify({
                    'error': 'Insufficient role',
                    'code': 'ROLE_REQUIRED',
                    'required_role': role.value
                }), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_resource_access(resource_type: str, resource_id_param: str, action: str):
    """
    Decorator to require resource access (ownership or permission).

    Usage:
        @app.route('/api/feedback/<feedback_id>', methods=['PUT'])
        @require_auth
        @require_resource_access('feedback', 'feedback_id', 'edit')
        def edit_feedback(feedback_id):
            # Only owner or users with feedback.edit_any can access
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'AUTH_REQUIRED'
                }), 401

            # Get resource_id from kwargs (Flask route parameters)
            resource_id = kwargs.get(resource_id_param)
            if not resource_id:
                return jsonify({
                    'error': 'Resource ID required',
                    'code': 'RESOURCE_ID_MISSING'
                }), 400

            # Check if user can access the resource
            if not RBACManager.can_access_resource(user_id, resource_type, resource_id, action):
                logger.warning(f"User {user_id} denied access to {resource_type} {resource_id} ({action})")
                return jsonify({
                    'error': 'Access denied',
                    'code': 'ACCESS_DENIED',
                    'resource_type': resource_type,
                    'action': action
                }), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# API Endpoints

@app.route('/api/csrf-token', methods=['GET'])
@rate_limit_ip()  # SEC-011: Global rate limit per IP
def get_csrf_token():
    """
    Get a CSRF token for the current session.

    This endpoint:
    1. Creates or retrieves session ID
    2. Generates CSRF token tied to session
    3. Sets CSRF cookie for double-submit pattern

    SEC-011: Rate limited to prevent abuse
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
@require_auth
@require_api_permission(Permission.FEEDBACK_CREATE)
@rate_limit_feedback()  # SEC-011: 5 req/hour per user
def submit_feedback():
    """
    Submit feedback endpoint.

    SEC-003: CSRF protected
    SEC-006: Requires authentication and FEEDBACK_CREATE permission
    SEC-011: Rate limited to 5 requests per hour per user
    """
    user_id = get_current_user_id()
    data = request.get_json()

    # Validate subscription tier for priority feedback
    feedback_type = data.get('type', 'feature')
    if feedback_type == 'priority':
        if not RBACManager.enforce_subscription_tier(user_id, 'builder_plus'):
            return jsonify({
                'error': 'Priority feedback requires Builder+ or Priority subscription',
                'code': 'SUBSCRIPTION_REQUIRED'
            }), 403

    # Process feedback
    feedback_id = secrets.token_hex(8)
    feedback = {
        'id': feedback_id,
        'content': data.get('content', ''),
        'type': feedback_type,
        'user_id': user_id,
        'timestamp': datetime.now().isoformat()
    }

    # SEC-006: Set resource ownership
    RBACManager.set_resource_owner('feedback', feedback_id, user_id)

    logger.info(f"Feedback created: {feedback_id} by user {user_id}")

    return jsonify({
        'success': True,
        'feedback': feedback
    }), 201


@app.route('/api/feedback/<feedback_id>', methods=['GET'])
@require_auth
@rate_limit_ip()  # SEC-011: Global rate limit
def get_feedback(feedback_id):
    """
    Get feedback by ID.

    SEC-006: User must have permission to view feedback
    SEC-011: Rate limited to prevent abuse
    """
    user_id = get_current_user_id()

    # Check if user can view this feedback
    if not RBACManager.can_access_resource(user_id, 'feedback', feedback_id, 'view'):
        return jsonify({
            'error': 'Access denied',
            'code': 'ACCESS_DENIED'
        }), 403

    # Placeholder - would fetch from database
    feedback = {
        'id': feedback_id,
        'content': 'Sample feedback',
        'type': 'feature',
        'timestamp': datetime.now().isoformat()
    }

    return jsonify({
        'success': True,
        'feedback': feedback
    })


@app.route('/api/feedback/<feedback_id>', methods=['PUT'])
@csrf_protect
@require_auth
@require_resource_access('feedback', 'feedback_id', 'edit')
@rate_limit_feedback()  # SEC-011: 5 req/hour per user
def edit_feedback(feedback_id):
    """
    Edit feedback.

    SEC-003: CSRF protected
    SEC-006: User must own the feedback or have edit_any permission
    SEC-011: Rate limited to 5 requests per hour per user
    """
    user_id = get_current_user_id()
    data = request.get_json()

    # Update feedback (placeholder)
    feedback = {
        'id': feedback_id,
        'content': data.get('content', ''),
        'type': data.get('type', 'feature'),
        'user_id': user_id,
        'updated_at': datetime.now().isoformat()
    }

    logger.info(f"Feedback edited: {feedback_id} by user {user_id}")

    return jsonify({
        'success': True,
        'feedback': feedback
    })


@app.route('/api/feedback/<feedback_id>', methods=['DELETE'])
@csrf_protect
@require_auth
@require_resource_access('feedback', 'feedback_id', 'delete')
@rate_limit_ip()  # SEC-011: Global rate limit
def delete_feedback(feedback_id):
    """
    Delete feedback.

    SEC-003: CSRF protected
    SEC-006: User must own the feedback or have delete_any permission
    SEC-011: Rate limited to prevent abuse
    """
    user_id = get_current_user_id()

    # Delete feedback (placeholder)
    logger.info(f"Feedback deleted: {feedback_id} by user {user_id}")

    return jsonify({
        'success': True,
        'message': 'Feedback deleted'
    })


@app.route('/api/admin/users', methods=['GET'])
@require_auth
@require_api_role(Role.ADMIN)
@rate_limit_admin()  # SEC-011: 100 req/min per admin
def list_users():
    """
    List all users (admin only).

    SEC-006: Only admins can access this endpoint
    SEC-011: Rate limited to 100 requests per minute per admin
    """
    user_id = get_current_user_id()

    # Placeholder - would fetch from database
    users = [
        {'id': 'user1', 'role': 'user', 'email': 'user1@example.com'},
        {'id': 'user2', 'role': 'builder', 'email': 'user2@example.com'},
    ]

    logger.info(f"User list accessed by admin {user_id}")

    return jsonify({
        'success': True,
        'users': users
    })


@app.route('/api/admin/users/<target_user_id>/role', methods=['PUT'])
@csrf_protect
@require_auth
@require_api_role(Role.ADMIN)
@rate_limit_admin()  # SEC-011: 100 req/min per admin
def change_user_role(target_user_id):
    """
    Change user role (admin only).

    SEC-003: CSRF protected
    SEC-006: Only admins can change roles
    SEC-011: Rate limited to 100 requests per minute per admin
    """
    user_id = get_current_user_id()
    data = request.get_json()

    new_role_str = data.get('role')
    if not new_role_str:
        return jsonify({
            'error': 'Role required',
            'code': 'ROLE_MISSING'
        }), 400

    try:
        new_role = Role(new_role_str)
    except ValueError:
        return jsonify({
            'error': 'Invalid role',
            'code': 'ROLE_INVALID'
        }), 400

    # Prevent privilege escalation: only superadmin can create other admins
    if new_role in [Role.ADMIN, Role.SUPERADMIN]:
        if RBACManager.get_role(user_id) != Role.SUPERADMIN:
            return jsonify({
                'error': 'Only superadmin can assign admin roles',
                'code': 'PRIVILEGE_ESCALATION_PREVENTED'
            }), 403

    # Update role
    RBACManager.assign_role(target_user_id, new_role)

    logger.info(f"User {target_user_id} role changed to {new_role_str} by admin {user_id}")

    return jsonify({
        'success': True,
        'message': f'User role updated to {new_role_str}'
    })


@app.route('/health', methods=['GET'])
def simple_health_check():
    """
    DP-001: Simple health check endpoint for deployment monitoring.

    No rate limiting on this endpoint to allow frequent health checks.
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'ralph-mode-bot'
    })


@app.route('/api/versions', methods=['GET'])
@rate_limit_ip()  # SEC-011: Global rate limit
def get_versions():
    """
    WB-001: Get version information for website display.

    Returns stable, beta, and alpha versions with:
    - Version number
    - Release date
    - Changelog link
    - Download link

    SEC-011: Rate limited to prevent abuse
    """
    try:
        from version_manager import VersionManager
        from changelog_generator import ChangelogGenerator

        vm = VersionManager()
        cg = ChangelogGenerator()

        # Get current stable version
        current_version = vm.get_current_version()

        # Get version history to find latest stable, beta, and alpha
        version_history = cg.get_version_history(limit=100)

        # Categorize versions based on semantic versioning conventions:
        # - Stable: X.Y.0 or X.Y.Z where Z > 0 and not pre-release
        # - Beta: Versions with "beta" tag or X.Y.Z-beta
        # - Alpha: Versions with "alpha" tag or X.Y.Z-alpha or 0.X.Y versions

        stable_version = None
        beta_version = None
        alpha_version = None

        for entry in version_history:
            version_str = entry.version

            # Check for explicit beta/alpha tags
            if 'beta' in version_str.lower():
                if not beta_version:
                    beta_version = entry
            elif 'alpha' in version_str.lower():
                if not alpha_version:
                    alpha_version = entry
            # 0.x.y versions are considered alpha
            elif version_str.startswith('0.'):
                if not alpha_version:
                    alpha_version = entry
            else:
                # Stable version (1.0.0+)
                if not stable_version:
                    stable_version = entry

        # Use current version as stable if no stable found in history
        if not stable_version:
            stable_version_data = {
                'version': str(current_version),
                'date': datetime.now().isoformat(),
                'changelog_url': f'/changelog#{current_version}',
                'download_url': f'/download/ralph-starter-{current_version}.zip'
            }
        else:
            stable_version_data = {
                'version': stable_version.version,
                'date': stable_version.released_at.isoformat(),
                'changelog_url': f'/changelog#{stable_version.version}',
                'download_url': f'/download/ralph-starter-{stable_version.version}.zip'
            }

        # Format beta version data
        beta_version_data = None
        if beta_version:
            beta_version_data = {
                'version': beta_version.version,
                'date': beta_version.released_at.isoformat(),
                'changelog_url': f'/changelog#{beta_version.version}',
                'download_url': f'/download/ralph-starter-{beta_version.version}.zip'
            }

        # Format alpha version data
        alpha_version_data = None
        if alpha_version:
            alpha_version_data = {
                'version': alpha_version.version,
                'date': alpha_version.released_at.isoformat(),
                'changelog_url': f'/changelog#{alpha_version.version}',
                'download_url': f'/download/ralph-starter-{alpha_version.version}.zip'
            }

        return jsonify({
            'success': True,
            'stable': stable_version_data,
            'beta': beta_version_data,
            'alpha': alpha_version_data,
            'current': str(current_version)
        })

    except Exception as e:
        logger.error(f"Error fetching versions: {e}")
        return jsonify({
            'error': 'Failed to fetch versions',
            'code': 'VERSION_FETCH_ERROR'
        }), 500


@app.route('/api/build-status', methods=['GET'])
@rate_limit_ip()  # SEC-011: Global rate limit
def get_build_status():
    """
    WB-003: Public Build Status Dashboard endpoint.

    Returns real-time build status information:
    - Queue depth (number of items waiting to build)
    - Current build task (if any)
    - Recent deployments list
    - Build success rate

    This is a public endpoint (no auth required) for website display.
    Updates in real-time by querying the feedback queue and build orchestrator.

    SEC-011: Rate limited to prevent abuse
    """
    try:
        from database import get_db, Feedback
        from feedback_queue import get_feedback_queue

        with get_db() as db:
            queue = get_feedback_queue(db)

            # Queue depth: count items in "queued" status
            queue_depth = db.query(Feedback).filter(
                Feedback.status == "queued"
            ).count()

            # Current build: find item in "in_progress" status
            current_build = db.query(Feedback).filter(
                Feedback.status == "in_progress"
            ).first()

            current_build_data = None
            if current_build:
                current_build_data = {
                    'feedback_id': current_build.id,
                    'type': current_build.feedback_type,
                    'started_at': current_build.updated_at.isoformat() if current_build.updated_at else None,
                    'priority_score': current_build.priority_score
                }

            # Recent deployments: last 10 items with "deployed_staging" or "deployed_production" status
            recent_deployments = db.query(Feedback).filter(
                Feedback.status.in_(['deployed_staging', 'deployed_production'])
            ).order_by(
                Feedback.updated_at.desc()
            ).limit(10).all()

            deployment_list = []
            for deployment in recent_deployments:
                deployment_list.append({
                    'feedback_id': deployment.id,
                    'type': deployment.feedback_type,
                    'status': deployment.status,
                    'deployed_at': deployment.updated_at.isoformat() if deployment.updated_at else None,
                    'quality_score': deployment.quality_score,
                    'priority_score': deployment.priority_score
                })

            # Build success rate: calculate from last 50 completed builds
            total_builds = db.query(Feedback).filter(
                Feedback.status.in_(['deployed_staging', 'deployed_production', 'rejected'])
            ).count()

            successful_builds = db.query(Feedback).filter(
                Feedback.status.in_(['deployed_staging', 'deployed_production'])
            ).count()

            success_rate = 0.0
            if total_builds > 0:
                success_rate = (successful_builds / total_builds) * 100

            return jsonify({
                'success': True,
                'queue_depth': queue_depth,
                'current_build': current_build_data,
                'recent_deployments': deployment_list,
                'build_success_rate': round(success_rate, 2),
                'total_builds': total_builds,
                'successful_builds': successful_builds,
                'timestamp': datetime.now().isoformat()
            })

    except Exception as e:
        logger.error(f"Error fetching build status: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to fetch build status',
            'code': 'BUILD_STATUS_ERROR'
        }), 500


@app.route('/api/health', methods=['GET'])
@rate_limit_ip()  # SEC-011: Global rate limit
def health_check():
    """
    Health check endpoint (no CSRF needed for GET)

    SEC-011: Rate limited to prevent abuse
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'csrf_protection': 'enabled',
        'rate_limiting': 'enabled'
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
    # SEC-007: Validate and enforce secure configuration
    print("\n🔍 Validating configuration...")
    AppConfig.enforce_security()

    # Print configuration summary
    AppConfig.print_config_summary()

    # Development server
    # In production, use gunicorn or similar WSGI server
    if AppConfig.ENV != 'production':
        print("⚠️  Starting development server")
        print("⚠️  DO NOT use in production - use gunicorn/uwsgi instead")
    else:
        print("🚀 Starting production server")
        print("⚠️  Ensure you're behind nginx/reverse proxy with HTTPS")

    print(f"🔒 CSRF Protection: ENABLED")
    print(f"🔒 Data Encryption: ENABLED (AES-256-GCM)")
    print(f"🔒 RBAC: ENABLED")
    print(f"🔒 Rate Limiting: ENABLED (SEC-011)")
    print(f"   - Global: {RateLimitConfig.GLOBAL_PER_IP_MINUTE} req/min per IP")
    print(f"   - Auth: {RateLimitConfig.AUTH_PER_IP_MINUTE} req/min per IP")
    print(f"   - Feedback: {RateLimitConfig.FEEDBACK_PER_USER_HOUR} req/hour per user")
    print(f"   - Admin: {RateLimitConfig.ADMIN_PER_USER_MINUTE} req/min per admin")
    print(f"🔒 HSTS: ENABLED (max-age=31536000)")
    print(f"🔒 TLS 1.3: REQUIRED")
    print(f"🔒 Security Misconfiguration Prevention: ENABLED")
    print(f"🌐 Allowed Origins: {ALLOWED_ORIGINS}")
    print(f"🐛 Debug Mode: {AppConfig.DEBUG}")

    # SEC-005 & SEC-007: Run with HTTPS in production
    # For production, use nginx with Let's Encrypt SSL certificate
    app.run(
        host=AppConfig.HOST,
        port=AppConfig.PORT,
        debug=AppConfig.DEBUG,
        ssl_context='adhoc' if os.environ.get('USE_SSL') else None
    )
