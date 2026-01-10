#!/usr/bin/env python3
"""
Rate Limiting Module for Ralph Mode

SEC-011: API Rate Limiting
Implements comprehensive rate limiting with:
- Per-IP rate limits (global and endpoint-specific)
- Per-user rate limits
- Redis-based distributed rate limiting
- 429 Too Many Requests responses with proper headers
- Multiple time windows (per-minute, per-hour, per-day)
"""

import time
import hashlib
import logging
from typing import Optional, Dict, Tuple, Any
from functools import wraps
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock

from flask import request, jsonify

# Try to import Redis, fall back to in-memory if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available - using in-memory rate limiting (not suitable for distributed systems)")


logger = logging.getLogger(__name__)


class RateLimitConfig:
    """
    Rate limit configuration for different endpoints and scopes.

    SEC-011 Requirements:
    - Global rate limit: 1000 req/min per IP
    - Auth endpoints: 10 req/min per IP
    - Feedback endpoint: 5 req/hour per user
    - Admin endpoints: 100 req/min per admin
    """

    # Global limits (per IP)
    GLOBAL_PER_IP_MINUTE = 1000
    GLOBAL_PER_IP_HOUR = 10000

    # Auth endpoints (per IP)
    AUTH_PER_IP_MINUTE = 10
    AUTH_PER_IP_HOUR = 50

    # Feedback endpoints (per user)
    FEEDBACK_PER_USER_HOUR = 5
    FEEDBACK_PER_USER_DAY = 20

    # Admin endpoints (per admin user)
    ADMIN_PER_USER_MINUTE = 100
    ADMIN_PER_USER_HOUR = 1000

    # Redis configuration
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_PASSWORD = None

    # Rate limit window durations (seconds)
    WINDOW_MINUTE = 60
    WINDOW_HOUR = 3600
    WINDOW_DAY = 86400

    @classmethod
    def get_limit_for_endpoint(cls, endpoint: str, scope: str = 'ip') -> Dict[str, int]:
        """
        Get rate limit configuration for a specific endpoint.

        Args:
            endpoint: The API endpoint path
            scope: 'ip' or 'user'

        Returns:
            Dict with 'limit' and 'window' keys
        """
        # Auth endpoints
        if '/api/auth' in endpoint or '/api/login' in endpoint or '/api/register' in endpoint:
            return {
                'limit': cls.AUTH_PER_IP_MINUTE,
                'window': cls.WINDOW_MINUTE,
                'name': 'auth_per_ip_minute'
            }

        # Feedback endpoints
        if '/api/feedback' in endpoint:
            if scope == 'user':
                return {
                    'limit': cls.FEEDBACK_PER_USER_HOUR,
                    'window': cls.WINDOW_HOUR,
                    'name': 'feedback_per_user_hour'
                }

        # Admin endpoints
        if '/api/admin' in endpoint:
            if scope == 'user':
                return {
                    'limit': cls.ADMIN_PER_USER_MINUTE,
                    'window': cls.WINDOW_MINUTE,
                    'name': 'admin_per_user_minute'
                }

        # Global default (per IP)
        return {
            'limit': cls.GLOBAL_PER_IP_MINUTE,
            'window': cls.WINDOW_MINUTE,
            'name': 'global_per_ip_minute'
        }


class InMemoryRateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    WARNING: This is not suitable for distributed systems!
    Use RedisRateLimiter for production with multiple servers.
    """

    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.lock = Lock()

    def is_allowed(
        self,
        key: str,
        limit: int,
        window: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a request is allowed under rate limits.

        Args:
            key: Unique identifier for the rate limit bucket
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (is_allowed, metadata)
            metadata includes: remaining, reset_time, retry_after
        """
        with self.lock:
            now = time.time()
            cutoff = now - window

            # Clean old requests
            if key in self.requests:
                self.requests[key] = [
                    req_time for req_time in self.requests[key]
                    if req_time > cutoff
                ]

            # Check if limit exceeded
            current_count = len(self.requests[key])

            if current_count >= limit:
                # Calculate when the oldest request will expire
                oldest_request = min(self.requests[key]) if self.requests[key] else now
                reset_time = oldest_request + window
                retry_after = int(reset_time - now)

                return False, {
                    'limit': limit,
                    'remaining': 0,
                    'reset': int(reset_time),
                    'retry_after': retry_after
                }

            # Allow request and record it
            self.requests[key].append(now)
            reset_time = now + window

            return True, {
                'limit': limit,
                'remaining': limit - current_count - 1,
                'reset': int(reset_time),
                'retry_after': 0
            }

    def reset(self, key: str):
        """Reset rate limit for a specific key (for testing)"""
        with self.lock:
            if key in self.requests:
                del self.requests[key]


class RedisRateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm.

    This implementation is suitable for distributed systems.
    Uses Redis sorted sets to track request timestamps.
    """

    def __init__(
        self,
        host: str = RateLimitConfig.REDIS_HOST,
        port: int = RateLimitConfig.REDIS_PORT,
        db: int = RateLimitConfig.REDIS_DB,
        password: Optional[str] = RateLimitConfig.REDIS_PASSWORD
    ):
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"✅ Connected to Redis at {host}:{port}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise

    def is_allowed(
        self,
        key: str,
        limit: int,
        window: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a request is allowed under rate limits using Redis.

        Uses a sliding window algorithm with Redis sorted sets:
        - Score = timestamp
        - Members = unique request IDs
        - Remove old entries outside the window
        - Count entries within the window

        Args:
            key: Unique identifier for the rate limit bucket
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (is_allowed, metadata)
        """
        try:
            now = time.time()
            cutoff = now - window

            # Redis key for this rate limit bucket
            redis_key = f"rate_limit:{key}"

            # Pipeline for atomic operations
            pipe = self.redis_client.pipeline()

            # Remove old entries (outside the window)
            pipe.zremrangebyscore(redis_key, 0, cutoff)

            # Count current requests in window
            pipe.zcard(redis_key)

            # Execute pipeline
            results = pipe.execute()
            current_count = results[1]  # Result of ZCARD

            if current_count >= limit:
                # Get oldest request timestamp
                oldest = self.redis_client.zrange(redis_key, 0, 0, withscores=True)
                if oldest:
                    oldest_time = oldest[0][1]
                    reset_time = oldest_time + window
                else:
                    reset_time = now + window

                retry_after = int(reset_time - now)

                return False, {
                    'limit': limit,
                    'remaining': 0,
                    'reset': int(reset_time),
                    'retry_after': retry_after
                }

            # Add current request
            request_id = f"{now}:{hashlib.sha256(str(now).encode()).hexdigest()[:8]}"
            self.redis_client.zadd(redis_key, {request_id: now})

            # Set expiration on the key (cleanup)
            self.redis_client.expire(redis_key, window * 2)

            reset_time = now + window

            return True, {
                'limit': limit,
                'remaining': limit - current_count - 1,
                'reset': int(reset_time),
                'retry_after': 0
            }

        except redis.RedisError as e:
            logger.error(f"Redis error in rate limiter: {e}")
            # Fail open (allow request) rather than fail closed
            # This prevents Redis outages from breaking the API
            logger.warning("Rate limiter failing open due to Redis error")
            return True, {
                'limit': limit,
                'remaining': limit,
                'reset': int(time.time() + window),
                'retry_after': 0
            }

    def reset(self, key: str):
        """Reset rate limit for a specific key (for testing)"""
        redis_key = f"rate_limit:{key}"
        self.redis_client.delete(redis_key)


class RateLimiter:
    """
    Main rate limiter class that chooses between Redis and in-memory.

    Automatically uses Redis if available, falls back to in-memory.
    """

    _instance = None
    _backend = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._initialize_backend()
        return cls._instance

    @classmethod
    def _initialize_backend(cls):
        """Initialize the rate limiting backend (Redis or in-memory)"""
        if REDIS_AVAILABLE:
            try:
                cls._backend = RedisRateLimiter()
                logger.info("✅ Using Redis-based rate limiting (distributed)")
            except Exception as e:
                logger.warning(f"⚠️  Redis unavailable, falling back to in-memory: {e}")
                cls._backend = InMemoryRateLimiter()
        else:
            logger.warning("⚠️  Using in-memory rate limiting (not suitable for production)")
            cls._backend = InMemoryRateLimiter()

    @classmethod
    def check_rate_limit(
        cls,
        identifier: str,
        limit: int,
        window: int,
        scope: str = 'ip'
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a request is allowed.

        Args:
            identifier: IP address or user ID
            limit: Maximum requests allowed
            window: Time window in seconds
            scope: 'ip' or 'user'

        Returns:
            Tuple of (is_allowed, metadata)
        """
        # Create unique key for this rate limit bucket
        key = f"{scope}:{identifier}"

        return cls._backend.is_allowed(key, limit, window)

    @classmethod
    def reset(cls, identifier: str, scope: str = 'ip'):
        """Reset rate limit for testing"""
        key = f"{scope}:{identifier}"
        cls._backend.reset(key)


def get_client_ip() -> str:
    """
    Get client IP address, handling proxies correctly.

    Checks X-Forwarded-For header for proxied requests.
    """
    # Check if behind a proxy
    if 'X-Forwarded-For' in request.headers:
        # X-Forwarded-For can contain multiple IPs, take the first (client)
        ip = request.headers['X-Forwarded-For'].split(',')[0].strip()
    else:
        ip = request.remote_addr

    return ip or '0.0.0.0'


def get_user_id() -> Optional[str]:
    """
    Get authenticated user ID from session.

    Returns None if not authenticated.
    """
    from flask import session
    return session.get('user_id')


def rate_limit(
    scope: str = 'ip',
    custom_limit: Optional[int] = None,
    custom_window: Optional[int] = None
):
    """
    Decorator to apply rate limiting to Flask endpoints.

    SEC-011: Implements comprehensive rate limiting per acceptance criteria.

    Usage:
        @app.route('/api/feedback', methods=['POST'])
        @rate_limit(scope='user')
        def submit_feedback():
            # Only 5 requests per hour per user

        @app.route('/api/auth/login', methods=['POST'])
        @rate_limit(scope='ip')
        def login():
            # Only 10 requests per minute per IP

    Args:
        scope: 'ip' for IP-based limiting, 'user' for user-based limiting
        custom_limit: Override default limit
        custom_window: Override default window (seconds)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get identifier based on scope
            if scope == 'user':
                identifier = get_user_id()
                if not identifier:
                    # Not authenticated, fall back to IP-based limiting
                    identifier = get_client_ip()
                    actual_scope = 'ip'
                else:
                    actual_scope = 'user'
            else:
                identifier = get_client_ip()
                actual_scope = 'ip'

            # Get rate limit configuration for this endpoint
            limit_config = RateLimitConfig.get_limit_for_endpoint(
                request.path,
                actual_scope
            )

            # Allow custom overrides
            limit = custom_limit or limit_config['limit']
            window = custom_window or limit_config['window']

            # Check rate limit
            allowed, metadata = RateLimiter.check_rate_limit(
                identifier,
                limit,
                window,
                actual_scope
            )

            if not allowed:
                # SEC-011: Return 429 with Retry-After header
                logger.warning(
                    f"Rate limit exceeded for {actual_scope}={identifier} "
                    f"on {request.path} (limit={limit}/{window}s)"
                )

                response = jsonify({
                    'error': 'Too Many Requests',
                    'message': f'Rate limit exceeded. Try again in {metadata["retry_after"]} seconds.',
                    'code': 'RATE_LIMIT_EXCEEDED',
                    'limit': metadata['limit'],
                    'retry_after': metadata['retry_after']
                })
                response.status_code = 429

                # SEC-011: Add rate limit headers
                response.headers['X-RateLimit-Limit'] = str(metadata['limit'])
                response.headers['X-RateLimit-Remaining'] = str(metadata['remaining'])
                response.headers['X-RateLimit-Reset'] = str(metadata['reset'])
                response.headers['Retry-After'] = str(metadata['retry_after'])

                return response

            # Request allowed - add rate limit headers to response
            response = f(*args, **kwargs)

            # SEC-011: Add rate limit headers to successful responses too
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(metadata['limit'])
                response.headers['X-RateLimit-Remaining'] = str(metadata['remaining'])
                response.headers['X-RateLimit-Reset'] = str(metadata['reset'])

            return response

        return decorated_function
    return decorator


# Convenience decorators for common use cases
def rate_limit_ip(limit: Optional[int] = None, window: Optional[int] = None):
    """Rate limit by IP address"""
    return rate_limit(scope='ip', custom_limit=limit, custom_window=window)


def rate_limit_user(limit: Optional[int] = None, window: Optional[int] = None):
    """Rate limit by authenticated user"""
    return rate_limit(scope='user', custom_limit=limit, custom_window=window)


def rate_limit_auth():
    """
    Rate limit for authentication endpoints.
    SEC-011: 10 req/min per IP
    """
    return rate_limit(
        scope='ip',
        custom_limit=RateLimitConfig.AUTH_PER_IP_MINUTE,
        custom_window=RateLimitConfig.WINDOW_MINUTE
    )


def rate_limit_feedback():
    """
    Rate limit for feedback endpoints.
    SEC-011: 5 req/hour per user
    """
    return rate_limit(
        scope='user',
        custom_limit=RateLimitConfig.FEEDBACK_PER_USER_HOUR,
        custom_window=RateLimitConfig.WINDOW_HOUR
    )


def rate_limit_admin():
    """
    Rate limit for admin endpoints.
    SEC-011: 100 req/min per admin
    """
    return rate_limit(
        scope='user',
        custom_limit=RateLimitConfig.ADMIN_PER_USER_MINUTE,
        custom_window=RateLimitConfig.WINDOW_MINUTE
    )


if __name__ == '__main__':
    # Test the rate limiter
    print("\n🧪 Testing Rate Limiter\n")

    # Test in-memory rate limiter
    limiter = InMemoryRateLimiter()

    print("Testing rate limit of 5 requests per 10 seconds:")
    for i in range(7):
        allowed, metadata = limiter.is_allowed("test_user", limit=5, window=10)
        print(f"Request {i+1}: {'✅ Allowed' if allowed else '❌ Blocked'} - {metadata}")

    print("\n✅ Rate limiter tests completed")
