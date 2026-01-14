"""
Ralph Mode Website - Flask Application
A hacker terminal aesthetic recipe generator with Google OAuth
"""

import os
import uuid
from datetime import timedelta
from flask import Flask, render_template, session, redirect, url_for, request, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from groq import Groq
from config import get_config

# Initialize Flask app
app = Flask(__name__)
config = get_config()
app.config.from_object(config)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    """User model for Google OAuth authentication."""

    def __init__(self, user_info):
        self.id = user_info.get('sub')
        self.name = user_info.get('name')
        self.email = user_info.get('email')
        self.picture = user_info.get('picture')


@login_manager.user_loader
def load_user(user_id):
    """Load user from session."""
    if 'user_info' in session and session['user_info'].get('sub') == user_id:
        return User(session['user_info'])
    return None


# ===== ROUTES =====

@app.route('/')
def index():
    """Landing page - terminal style."""
    return render_template('index.html')


@app.route('/login')
def login():
    """Login page with Google OAuth button."""
    return render_template('login.html', google_client_id=app.config['GOOGLE_CLIENT_ID'])


@app.route('/auth/callback')
def auth_callback():
    """Google OAuth callback handler."""
    # In production, verify the CSRF token
    csrf_token_cookie = request.cookies.get('g_csrf_token')
    if not csrf_token_cookie:
        return "Missing CSRF token", 400

    # Verify the CSRF token
    csrf_token_body = request.args.get('csrf_token')
    if not csrf_token_body or csrf_token_cookie != csrf_token_body:
        return "Invalid CSRF token", 400

    # Verify the Google ID token
    token = request.args.get('credential')
    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            app.config['GOOGLE_CLIENT_ID']
        )

        # Store user in session
        session['user_info'] = idinfo
        user = User(idinfo)
        login_user(user, remember=True, duration=timedelta(days=30))

        return redirect(url_for('dashboard'))

    except ValueError as e:
        return f"Invalid token: {e}", 400


@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with saved recipes."""
    return render_template('dashboard.html', user=current_user)


@app.route('/generate')
@login_required
def generate():
    """Recipe generation page."""
    return render_template('generate.html', user=current_user)


@app.route('/api/generate', methods=['POST'])
@login_required
def api_generate():
    """Generate a recipe using Groq AI."""
    data = request.get_json()
    prompt = data.get('prompt', '')

    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400

    try:
        client = Groq(api_key=app.config.get('GROQ_API_KEY'))
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are Ralph, a chaotic but brilliant chef. Generate recipes in a specific format: Recipe Name, Ingredients (with measurements), Instructions (numbered steps), and a fun 'Ralph Tip'. Be creative but the recipe must actually work."
                },
                {
                    "role": "user",
                    "content": f"Create a recipe for: {prompt}"
                }
            ],
            temperature=0.8,
            max_tokens=1000
        )

        recipe = completion.choices[0].message.content
        return jsonify({'recipe': recipe})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/logout')
@login_required
def logout():
    """Logout user."""
    session.clear()
    logout_user()
    return redirect(url_for('index'))


@app.route('/health')
def health():
    """Health check for Render."""
    return jsonify({'status': 'healthy', 'service': 'ralphmode.com'}), 200


# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message="Command not found"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', code=500, message="System failure"), 500


if __name__ == '__main__':
    # Validate config in development
    if app.config['DEBUG']:
        try:
            config.validate_required()
        except ValueError as e:
            print(f"WARNING: {e}")
            print("Set up your .env file before running in production!")

    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])
