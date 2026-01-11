#!/usr/bin/env python3
"""
SEC-001: Secure Database Layer for Ralph Mode Bot

This module provides SQL injection-safe database operations using:
- SQLAlchemy ORM for all database queries (no raw SQL concatenation)
- Parameterized queries for any raw SQL needs
- Input validation before any DB operation
- Prepared statements via SQLAlchemy's text() function

SECURITY PRINCIPLES:
1. NEVER use string concatenation/f-strings for SQL queries
2. ALWAYS use ORM methods or parameterized queries
3. VALIDATE all input before database operations
4. USE read-only sessions where possible
5. ESCAPE any user-provided identifiers

Usage:
    from database import get_db, User, Session, Feedback

    # Safe ORM query (recommended)
    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == user_id).first()

    # Safe parameterized query (when raw SQL needed)
    with get_db() as db:
        result = db.execute(
            text("SELECT * FROM users WHERE telegram_id = :id"),
            {"id": user_id}
        )
"""

import os
import re
import logging
from datetime import datetime
from typing import Optional, List, Any, Generator
from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    Float,
    ForeignKey,
    Index,
    event,
    text
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session as SQLSession, relationship
from sqlalchemy.pool import StaticPool

# SEC-020: Import PII encryption for data at rest
try:
    from pii_handler import encrypt_pii, decrypt_pii, PIIField, mask_for_logs
    PII_ENCRYPTION_AVAILABLE = True
except ImportError:
    PII_ENCRYPTION_AVAILABLE = False
    def encrypt_pii(value): return value
    def decrypt_pii(value): return value
    def mask_for_logs(value, field_name=None): return str(value)
    logging.warning("SEC-020: PII encryption not available - data stored in plaintext")

logger = logging.getLogger(__name__)

# Database configuration
# Use SQLite for local development (as per PRD blockers section)
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///ralph_mode.db"
)

# SEC-018: Use secure engine with connection pooling, SSL/TLS, and audit logging
try:
    from db_config import get_secure_engine
    # Use secure engine with all SEC-018 protections
    engine = get_secure_engine(DATABASE_URL)
    logger.info("SEC-018: Using secure database engine with encryption and audit logging")
except ImportError:
    # Fallback to basic engine if db_config not available
    logger.warning("SEC-018: db_config not found, using basic engine")
    # For SQLite, we need special handling for thread safety
    if DATABASE_URL.startswith("sqlite"):
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False  # Set to True for SQL debugging
        )
    else:
        # PostgreSQL or other databases
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,   # Recycle connections after 1 hour
            echo=False
        )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# =============================================================================
# SEC-001: Input Validation Utilities
# =============================================================================

class InputValidator:
    """
    Validates and sanitizes user input before database operations.

    This is the FIRST line of defense against SQL injection.
    Even with ORM/parameterized queries, input validation adds defense-in-depth.
    """

    # Patterns that might indicate SQL injection attempts
    SQL_INJECTION_PATTERNS = [
        r"(\s|^)(OR|AND)\s+\d+\s*=\s*\d+",  # OR 1=1, AND 1=1
        r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE)",  # SQL commands after semicolon
        r"--\s*$",  # SQL comment at end
        r"--(?=\s|$)",  # SQL comment (-- followed by space or end)
        r"'\s*#\s*$",  # MySQL comment style (admin'#)
        r"#\s*$",  # MySQL comment at end of string
        r"/\*.*\*/",  # Block comments
        r"UNION\s+(ALL\s+)?SELECT",  # Union-based injection
        r"'\s*(OR|AND)\s*'",  # String-based OR/AND injection
        r"\)\s*(OR|AND)\s*\(",  # Parenthesis-based OR/AND injection: ') OR ('
        r"xp_cmdshell",  # SQL Server command execution
        r"EXEC(\s+|\().*(@|sp_)",  # Stored procedure calls
        r"WAITFOR\s+DELAY",  # Time-based injection
        r"BENCHMARK\s*\(",  # MySQL time-based injection
    ]

    @classmethod
    def is_safe_string(cls, value: str, max_length: int = 10000) -> bool:
        """
        Check if a string is safe for database operations.

        Args:
            value: The string to validate
            max_length: Maximum allowed length

        Returns:
            True if the string appears safe, False otherwise
        """
        if not isinstance(value, str):
            return False

        if len(value) > max_length:
            logger.warning(f"Input exceeds max length: {len(value)} > {max_length}")
            return False

        # Check for SQL injection patterns
        upper_value = value.upper()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, upper_value, re.IGNORECASE):
                logger.warning(f"Potential SQL injection detected: {pattern}")
                return False

        return True

    @classmethod
    def sanitize_identifier(cls, identifier: str) -> str:
        """
        Sanitize a database identifier (table name, column name).

        NEVER use this for user-provided data in queries!
        Only use for dynamic column selection from a WHITELIST.

        Args:
            identifier: The identifier to sanitize

        Returns:
            Sanitized identifier containing only alphanumeric and underscore
        """
        # Remove anything that's not alphanumeric or underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '', identifier)

        # Ensure it doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized

        return sanitized[:64]  # Limit length

    @classmethod
    def validate_telegram_id(cls, telegram_id: Any) -> Optional[int]:
        """
        Validate and convert a Telegram user ID.

        Args:
            telegram_id: The ID to validate

        Returns:
            Integer ID if valid, None otherwise
        """
        try:
            id_int = int(telegram_id)
            # Telegram IDs are positive integers
            if id_int > 0:
                return id_int
        except (TypeError, ValueError):
            pass
        return None

    @classmethod
    def validate_chat_id(cls, chat_id: Any) -> Optional[int]:
        """
        Validate and convert a Telegram chat ID.

        Args:
            chat_id: The ID to validate

        Returns:
            Integer ID if valid, None otherwise
        """
        try:
            id_int = int(chat_id)
            # Chat IDs can be negative (for groups) or positive
            return id_int
        except (TypeError, ValueError):
            return None


# =============================================================================
# Database Models (SQLAlchemy ORM)
# =============================================================================

class User(Base):
    """User model - stores Telegram user information."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    subscription_tier = Column(String(50), default="free")  # free, builder, priority, enterprise
    access_tier = Column(Integer, default=4)  # MU-001: User tier (1=Owner, 2=Power, 3=Chatter, 4=Viewer)
    assigned_character = Column(String(100), nullable=True)  # MU-003: Springfield character assignment
    theme_preference = Column(String(50), default="colorful")  # OB-040: Visual theme (light, dark, colorful, minimal, custom)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_banned = Column(Boolean, default=False)
    ban_reason = Column(Text, nullable=True)
    quality_score = Column(Float, default=50.0)  # User reputation (0-100)
    version_preference = Column(String(20), default="stable")  # VM-003: stable, beta, alpha

    # Relationships
    sessions = relationship("BotSession", back_populates="user", lazy="dynamic")
    feedback = relationship("Feedback", back_populates="user", lazy="dynamic")

    def __repr__(self):
        # SEC-020: Mask PII in repr for safe logging
        masked_username = mask_for_logs(self.username, PIIField.USERNAME) if self.username else None
        return f"<User(telegram_id={self.telegram_id}, username={masked_username})>"

    # SEC-020: PII encryption helpers
    def set_encrypted_first_name(self, value: Optional[str]):
        """Set first_name with encryption (if available)."""
        if PII_ENCRYPTION_AVAILABLE and value:
            self.first_name = encrypt_pii(value)
        else:
            self.first_name = value

    def get_decrypted_first_name(self) -> Optional[str]:
        """Get decrypted first_name (if encrypted)."""
        if PII_ENCRYPTION_AVAILABLE and self.first_name:
            return decrypt_pii(self.first_name)
        return self.first_name

    def set_encrypted_last_name(self, value: Optional[str]):
        """Set last_name with encryption (if available)."""
        if PII_ENCRYPTION_AVAILABLE and value:
            self.last_name = encrypt_pii(value)
        else:
            self.last_name = value

    def get_decrypted_last_name(self) -> Optional[str]:
        """Get decrypted last_name (if encrypted)."""
        if PII_ENCRYPTION_AVAILABLE and self.last_name:
            return decrypt_pii(self.last_name)
        return self.last_name


class BotSession(Base):
    """Bot session model - tracks active coding sessions."""

    __tablename__ = "bot_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    chat_id = Column(Integer, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="active")  # active, completed, aborted
    project_name = Column(String(255), nullable=True)
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    session_data = Column(Text, nullable=True)  # JSON blob for session state

    # Relationships
    user = relationship("User", back_populates="sessions")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_session_status_user", "status", "user_id"),
    )

    def __repr__(self):
        return f"<BotSession(id={self.id}, user_id={self.user_id}, status={self.status})>"


class Feedback(Base):
    """User feedback model - for RLHF feedback loop."""

    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    feedback_type = Column(String(50), nullable=False)  # bug, feature, improvement, praise
    content = Column(Text, nullable=False)
    quality_score = Column(Float, nullable=True)  # AI-assessed quality (0-100)
    priority_score = Column(Float, nullable=True)  # Calculated priority
    status = Column(String(50), default="pending")  # pending, reviewing, building, deployed, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ip_hash = Column(String(64), nullable=True)  # Hashed IP for rate limiting
    is_duplicate_of = Column(Integer, ForeignKey("feedback.id"), nullable=True)
    upvote_count = Column(Integer, default=0, nullable=False)  # DD-002: Track duplicate merges as upvotes
    rejection_reason = Column(Text, nullable=True)  # SP-001: Reason for spam/duplicate rejection
    rejected_at = Column(DateTime, nullable=True)  # SP-001: When feedback was rejected
    consecutive_failures = Column(Integer, default=0, nullable=False)  # BO-003: Track consecutive build failures

    # Relationships
    user = relationship("User", back_populates="feedback")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_feedback_status_priority", "status", "priority_score"),
    )

    def __repr__(self):
        return f"<Feedback(id={self.id}, type={self.feedback_type}, status={self.status})>"


class RateLimitEntry(Base):
    """Rate limit tracking model."""

    __tablename__ = "rate_limits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(255), nullable=False, index=True)  # IP hash or user ID
    identifier_type = Column(String(20), nullable=False)  # "ip" or "user"
    action = Column(String(50), nullable=False)  # "feedback", "api_call", etc.
    count = Column(Integer, default=1)
    window_start = Column(DateTime, default=datetime.utcnow)
    blocked_until = Column(DateTime, nullable=True)

    # Index for cleanup queries
    __table_args__ = (
        Index("idx_rate_limit_lookup", "identifier", "action", "window_start"),
    )

    def __repr__(self):
        return f"<RateLimitEntry(identifier={self.identifier[:8]}..., action={self.action})>"


class UserSatisfaction(Base):
    """
    AN-001: User Satisfaction Tracking

    Tracks user satisfaction after deployed fixes.
    Used for RLHF improvement and quality metrics.
    """

    __tablename__ = "user_satisfaction"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    feedback_id = Column(Integer, ForeignKey("feedback.id"), nullable=False, index=True)
    satisfied = Column(Boolean, nullable=False)  # True = thumbs up, False = thumbs down
    created_at = Column(DateTime, default=datetime.utcnow)
    comment = Column(Text, nullable=True)  # Optional user comment about satisfaction

    # Indexes for analytics queries
    __table_args__ = (
        Index("idx_satisfaction_feedback", "feedback_id"),
        Index("idx_satisfaction_user", "user_id", "created_at"),
    )

    def __repr__(self):
        emoji = "👍" if self.satisfied else "👎"
        return f"<UserSatisfaction(feedback_id={self.feedback_id}, satisfied={emoji})>"


# =============================================================================
# Database Session Management
# =============================================================================

@contextmanager
def get_db() -> Generator[SQLSession, None, None]:
    """
    Get a database session with automatic cleanup.

    Usage:
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == 123).first()

    This context manager ensures:
    - Session is properly closed after use
    - Transactions are rolled back on error
    - Connections are returned to the pool
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize the database schema.

    Creates all tables if they don't exist.
    Safe to call multiple times.
    """
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


# =============================================================================
# SEC-001: Safe Query Examples (Documentation)
# =============================================================================

class SafeQueries:
    """
    Example safe queries demonstrating SEC-001 compliance.

    These methods show the CORRECT way to query the database,
    preventing SQL injection attacks.
    """

    @staticmethod
    def get_user_by_telegram_id(db: SQLSession, telegram_id: int) -> Optional[User]:
        """
        SAFE: Get user by Telegram ID using ORM.

        The ORM automatically parameterizes the query:
        SELECT * FROM users WHERE telegram_id = ?
        """
        # Validate input first
        validated_id = InputValidator.validate_telegram_id(telegram_id)
        if validated_id is None:
            return None

        # Safe ORM query - SQLAlchemy handles parameterization
        return db.query(User).filter(User.telegram_id == validated_id).first()

    @staticmethod
    def get_user_by_username(db: SQLSession, username: str) -> Optional[User]:
        """
        SAFE: Get user by username using ORM.

        Even if username contains SQL injection attempts,
        SQLAlchemy properly escapes it.
        """
        # Validate input
        if not InputValidator.is_safe_string(username, max_length=255):
            logger.warning(f"Invalid username rejected: {username[:50]}...")
            return None

        # Safe ORM query
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def search_feedback(db: SQLSession, search_term: str, limit: int = 50) -> List[Feedback]:
        """
        SAFE: Search feedback content using parameterized LIKE.

        The % wildcards are added safely, not via string concatenation.
        """
        # Validate input
        if not InputValidator.is_safe_string(search_term, max_length=500):
            return []

        # Validate limit
        limit = min(max(1, limit), 100)  # Clamp to 1-100

        # Safe parameterized LIKE query
        # Note: Using ORM's contains() which properly escapes
        return (
            db.query(Feedback)
            .filter(Feedback.content.contains(search_term))
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_user_stats_raw(db: SQLSession, user_id: int) -> Optional[dict]:
        """
        SAFE: Example of parameterized raw SQL when ORM isn't sufficient.

        Use text() with named parameters - NEVER string concatenation!
        """
        # Validate input
        validated_id = InputValidator.validate_telegram_id(user_id)
        if validated_id is None:
            return None

        # Safe parameterized raw SQL using text()
        query = text("""
            SELECT
                u.telegram_id,
                u.username,
                COUNT(DISTINCT s.id) as total_sessions,
                COUNT(DISTINCT f.id) as total_feedback,
                u.quality_score
            FROM users u
            LEFT JOIN bot_sessions s ON u.id = s.user_id
            LEFT JOIN feedback f ON u.id = f.user_id
            WHERE u.telegram_id = :user_id
            GROUP BY u.id
        """)

        # Execute with parameter dict - SQLAlchemy handles escaping
        result = db.execute(query, {"user_id": validated_id}).first()

        if result:
            return {
                "telegram_id": result[0],
                "username": result[1],
                "total_sessions": result[2],
                "total_feedback": result[3],
                "quality_score": result[4]
            }
        return None

    @staticmethod
    def create_user(db: SQLSession, telegram_id: int, username: Optional[str] = None,
                    first_name: Optional[str] = None, last_name: Optional[str] = None) -> Optional[User]:
        """
        SAFE: Create a new user using ORM.

        All values are properly parameterized by SQLAlchemy.
        """
        # Validate required input
        validated_id = InputValidator.validate_telegram_id(telegram_id)
        if validated_id is None:
            return None

        # Validate optional strings
        if username and not InputValidator.is_safe_string(username, 255):
            username = None
        if first_name and not InputValidator.is_safe_string(first_name, 255):
            first_name = None
        if last_name and not InputValidator.is_safe_string(last_name, 255):
            last_name = None

        # Check if user already exists
        existing = db.query(User).filter(User.telegram_id == validated_id).first()
        if existing:
            return existing

        # Safe ORM create
        user = User(
            telegram_id=validated_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        db.add(user)
        db.flush()  # Get the ID without committing

        return user


# =============================================================================
# UNSAFE Examples (for documentation - DO NOT USE)
# =============================================================================

class UnsafeExamples:
    """
    !!! WARNING: DO NOT USE THESE METHODS !!!

    These are examples of VULNERABLE code patterns.
    They exist only to document what NOT to do.
    """

    @staticmethod
    def UNSAFE_get_user_BAD(db: SQLSession, username: str):
        """
        !!! VULNERABLE TO SQL INJECTION !!!

        NEVER DO THIS:
        - String concatenation in SQL queries
        - f-strings with user input
        - .format() with user input

        Attack example:
            username = "admin'; DROP TABLE users; --"
        """
        # !!! NEVER DO THIS !!!
        # query = f"SELECT * FROM users WHERE username = '{username}'"
        # db.execute(query)  # VULNERABLE!
        raise NotImplementedError("This method intentionally raises to prevent use")

    @staticmethod
    def UNSAFE_search_BAD(db: SQLSession, term: str):
        """
        !!! VULNERABLE TO SQL INJECTION !!!

        NEVER DO THIS:
        - Building LIKE clauses with string concatenation
        - Using % + term + % directly

        Attack example:
            term = "%'; DELETE FROM feedback; --"
        """
        # !!! NEVER DO THIS !!!
        # query = f"SELECT * FROM feedback WHERE content LIKE '%{term}%'"
        # db.execute(query)  # VULNERABLE!
        raise NotImplementedError("This method intentionally raises to prevent use")


# =============================================================================
# SQL Injection Testing Utilities
# =============================================================================

class SQLInjectionTester:
    """
    Utilities for testing SQL injection prevention.

    Use these in CI/CD to verify queries are safe.
    """

    # Common SQL injection payloads for testing
    INJECTION_PAYLOADS = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "1; DELETE FROM users",
        "' UNION SELECT * FROM users --",
        "admin'--",
        "' OR 1=1 --",
        "'; EXEC xp_cmdshell('dir'); --",
        "1' AND (SELECT COUNT(*) FROM users) > 0 --",
        "' WAITFOR DELAY '0:0:5' --",
        "1 AND 1=1",
        "1' AND '1'='1",
        "' OR 'x'='x",
        "admin' #",
        "') OR ('1'='1",
        "1 OR 1=1",
    ]

    @classmethod
    def test_input_validation(cls) -> dict:
        """
        Test that input validation catches injection attempts.

        Returns:
            Dict with test results
        """
        results = {
            "passed": 0,
            "failed": 0,
            "failures": []
        }

        for payload in cls.INJECTION_PAYLOADS:
            if InputValidator.is_safe_string(payload):
                results["failed"] += 1
                results["failures"].append(payload)
            else:
                results["passed"] += 1

        return results

    @classmethod
    def test_orm_safety(cls) -> dict:
        """
        Test that ORM queries properly parameterize dangerous inputs.

        This creates a test database and verifies queries don't break.
        """
        results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }

        # Create in-memory test database
        test_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=test_engine)
        TestSession = sessionmaker(bind=test_engine)

        with TestSession() as db:
            # Test that injection payloads don't break queries
            for payload in cls.INJECTION_PAYLOADS:
                try:
                    # This should not break or return unexpected results
                    result = db.query(User).filter(User.username == payload).first()
                    # If we get here without exception, the query was properly parameterized
                    results["passed"] += 1
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"{payload}: {str(e)}")

        return results


# =============================================================================
# Initialize on import (create tables if needed)
# =============================================================================

def setup_database():
    """
    Safe database setup function.

    Call this during application startup.
    """
    try:
        init_db()
        logger.info("SEC-001: Database layer initialized with SQL injection prevention")

        # SEC-018: Enable audit logging on sensitive tables
        try:
            from db_config import setup_audit_logging
            setup_audit_logging(engine)
            logger.info("SEC-018: Audit logging enabled on sensitive tables")
        except ImportError:
            logger.warning("SEC-018: db_config not found, audit logging not enabled")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


if __name__ == "__main__":
    # Run security tests when executed directly
    print("=" * 60)
    print("SEC-001: SQL Injection Prevention Tests")
    print("=" * 60)

    print("\n1. Testing Input Validation...")
    validation_results = SQLInjectionTester.test_input_validation()
    print(f"   Passed: {validation_results['passed']}")
    print(f"   Failed: {validation_results['failed']}")
    if validation_results['failures']:
        print(f"   Undetected payloads: {validation_results['failures']}")

    print("\n2. Testing ORM Safety...")
    orm_results = SQLInjectionTester.test_orm_safety()
    print(f"   Passed: {orm_results['passed']}")
    print(f"   Failed: {orm_results['failed']}")
    if orm_results['errors']:
        print(f"   Errors: {orm_results['errors']}")

    print("\n" + "=" * 60)
    if validation_results['failed'] == 0 and orm_results['failed'] == 0:
        print("✅ All SQL injection prevention tests PASSED")
    else:
        print("❌ Some tests FAILED - review and fix!")
    print("=" * 60)
