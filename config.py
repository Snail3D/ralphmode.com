"""
Ralph Mode Website Configuration
SECURITY: Loads ALL sensitive values from environment variables.
NEVER hardcode secrets in this file.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
# In production, these should be set directly in the environment
load_dotenv()


class Config:
    """Base configuration with security-first defaults."""

    # Security: SECRET_KEY is required, fail fast if missing
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError(
            "SECRET_KEY environment variable not set. "
            "Generate one with: openssl rand -hex 32"
        )

    # Flask environment
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = FLASK_ENV == 'development'

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}"
        f"/{os.getenv('DB_NAME')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Verify connections before using
        'pool_recycle': 3600,   # Recycle connections after 1 hour
    }

    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_DISCOVERY_URL = os.getenv(
        'GOOGLE_DISCOVERY_URL',
        'https://accounts.google.com/.well-known/openid-configuration'
    )

    # Cloudflare
    CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')
    CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
    CLOUDFLARE_ZONE_ID = os.getenv('CLOUDFLARE_ZONE_ID')

    # Session security (hardened defaults)
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = os.getenv('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

    # Telegram Bot (for bot integration)
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    OLLAMA_API_BASE = os.getenv('OLLAMA_API_BASE', 'http://localhost:11434')

    @staticmethod
    def validate_required():
        """Validate that all required configuration is present."""
        required = ['SECRET_KEY', 'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET']
        missing = [key for key in required if not os.getenv(key)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


class DevelopmentConfig(Config):
    """Development configuration with relaxed security for local testing."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # Allow HTTP locally
    TESTING = False


class ProductionConfig(Config):
    """Production configuration with maximum security."""
    DEBUG = False
    TESTING = False
    # Ensure secure cookies in production
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing configuration with in-memory database."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# Config dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env_name=None):
    """Get configuration based on environment name."""
    if env_name is None:
        env_name = os.getenv('FLASK_ENV', 'development')
    return config.get(env_name, config['default'])
