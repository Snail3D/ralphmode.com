#!/usr/bin/env python3
"""
SEC-012: API Input Validation - Additional Validators

Custom validation functions beyond Pydantic schemas.
Handles security-critical validations like path traversal, SQL injection patterns, XSS.
"""

import re
import os
from typing import Optional, List, Tuple
from pathlib import Path


# ====================
# Security Pattern Detection
# ====================

# SQL Injection patterns (basic detection)
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
    r"(--|;|\/\*|\*\/)",
    r"(\bOR\b.*=.*)",
    r"(\bAND\b.*=.*)",
    r"(1\s*=\s*1)",
    r"('.*OR.*'.*=.*')",
]

# XSS patterns (basic detection)
XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"onerror\s*=",
    r"onload\s*=",
    r"<iframe",
    r"<embed",
    r"<object",
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    r"\.\.",
    r"~",
    r"\/etc\/",
    r"\/var\/",
    r"\/usr\/",
    r"C:\\",
    r"\\\\",
]


def detect_sql_injection(text: str) -> Tuple[bool, Optional[str]]:
    """
    Detect potential SQL injection attempts.

    Returns:
        (is_suspicious, matched_pattern)
    """
    text_upper = text.upper()
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, text_upper, re.IGNORECASE):
            return True, pattern
    return False, None


def detect_xss(text: str) -> Tuple[bool, Optional[str]]:
    """
    Detect potential XSS (Cross-Site Scripting) attempts.

    Returns:
        (is_suspicious, matched_pattern)
    """
    for pattern in XSS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True, pattern
    return False, None


def detect_path_traversal(text: str) -> Tuple[bool, Optional[str]]:
    """
    Detect potential path traversal attempts.

    Returns:
        (is_suspicious, matched_pattern)
    """
    for pattern in PATH_TRAVERSAL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True, pattern
    return False, None


# ====================
# String Validation
# ====================

def validate_length(text: str, min_len: int = 0, max_len: int = 10000) -> Tuple[bool, Optional[str]]:
    """
    Validate string length is within bounds.

    Returns:
        (is_valid, error_message)
    """
    if len(text) < min_len:
        return False, f"Text too short (min {min_len} chars)"
    if len(text) > max_len:
        return False, f"Text too long (max {max_len} chars)"
    return True, None


def validate_alphanumeric(text: str, allow_underscore: bool = True, allow_dash: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Validate string contains only alphanumeric characters (and optionally _ and -).

    Returns:
        (is_valid, error_message)
    """
    pattern = r'^[a-zA-Z0-9'
    if allow_underscore:
        pattern += '_'
    if allow_dash:
        pattern += r'\-'
    pattern += r']+$'

    if not re.match(pattern, text):
        return False, "Contains invalid characters"
    return True, None


def validate_no_special_chars(text: str, allowed: str = "") -> Tuple[bool, Optional[str]]:
    """
    Validate string contains no special characters except those in allowed.

    Returns:
        (is_valid, error_message)
    """
    pattern = r'^[a-zA-Z0-9\s' + re.escape(allowed) + r']+$'
    if not re.match(pattern, text):
        return False, "Contains disallowed special characters"
    return True, None


# ====================
# Numeric Validation
# ====================

def validate_numeric_bounds(value: int | float, min_val: Optional[int | float] = None, max_val: Optional[int | float] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate numeric value is within bounds.

    Returns:
        (is_valid, error_message)
    """
    if min_val is not None and value < min_val:
        return False, f"Value too small (min {min_val})"
    if max_val is not None and value > max_val:
        return False, f"Value too large (max {max_val})"
    return True, None


def validate_positive(value: int | float) -> Tuple[bool, Optional[str]]:
    """
    Validate numeric value is positive (> 0).

    Returns:
        (is_valid, error_message)
    """
    if value <= 0:
        return False, "Value must be positive"
    return True, None


def validate_non_negative(value: int | float) -> Tuple[bool, Optional[str]]:
    """
    Validate numeric value is non-negative (>= 0).

    Returns:
        (is_valid, error_message)
    """
    if value < 0:
        return False, "Value cannot be negative"
    return True, None


# ====================
# File Validation
# ====================

def validate_filename(filename: str, allowed_extensions: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate filename is safe (no path traversal, valid extension).

    Args:
        filename: The filename to validate
        allowed_extensions: List of allowed extensions (e.g., ['.zip', '.txt'])

    Returns:
        (is_valid, error_message)
    """
    # Check for path traversal
    is_suspicious, pattern = detect_path_traversal(filename)
    if is_suspicious:
        return False, f"Filename contains path traversal pattern: {pattern}"

    # Check for directory separators
    if '/' in filename or '\\' in filename:
        return False, "Filename cannot contain path separators"

    # Check extension if provided
    if allowed_extensions:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [e.lower() for e in allowed_extensions]:
            return False, f"File extension not allowed (allowed: {', '.join(allowed_extensions)})"

    return True, None


def validate_file_size(size_bytes: int, max_size_bytes: int = 52428800) -> Tuple[bool, Optional[str]]:
    """
    Validate file size is within allowed limits.

    Args:
        size_bytes: File size in bytes
        max_size_bytes: Maximum allowed size (default: 50MB)

    Returns:
        (is_valid, error_message)
    """
    if size_bytes <= 0:
        return False, "File size must be positive"
    if size_bytes > max_size_bytes:
        max_mb = max_size_bytes / 1024 / 1024
        return False, f"File too large (max {max_mb:.0f}MB)"
    return True, None


def validate_mime_type(mime_type: str, allowed_types: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate MIME type is in allowed list.

    Returns:
        (is_valid, error_message)
    """
    if mime_type not in allowed_types:
        return False, f"MIME type not allowed (allowed: {', '.join(allowed_types)})"
    return True, None


# ====================
# URL & Domain Validation
# ====================

def validate_url(url: str, allowed_schemes: List[str] = ['http', 'https']) -> Tuple[bool, Optional[str]]:
    """
    Validate URL format and scheme.

    Returns:
        (is_valid, error_message)
    """
    import urllib.parse

    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in allowed_schemes:
            return False, f"URL scheme not allowed (allowed: {', '.join(allowed_schemes)})"
        if not parsed.netloc:
            return False, "Invalid URL: missing domain"
        return True, None
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"


def validate_domain(domain: str) -> Tuple[bool, Optional[str]]:
    """
    Validate domain name format.

    Returns:
        (is_valid, error_message)
    """
    # Basic domain validation regex
    pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    if not re.match(pattern, domain):
        return False, "Invalid domain format"
    return True, None


# ====================
# Telegram-Specific Validation
# ====================

def validate_telegram_user_id(user_id: int) -> Tuple[bool, Optional[str]]:
    """
    Validate Telegram user ID format.
    Telegram user IDs are positive integers up to 2^31 - 1.

    Returns:
        (is_valid, error_message)
    """
    if user_id <= 0:
        return False, "User ID must be positive"
    if user_id > 2147483647:  # 2^31 - 1
        return False, "User ID exceeds maximum value"
    return True, None


def validate_telegram_file_id(file_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Telegram file ID format.
    File IDs are alphanumeric with underscores and dashes.

    Returns:
        (is_valid, error_message)
    """
    if len(file_id) < 10 or len(file_id) > 200:
        return False, "File ID length invalid (10-200 chars)"

    if not re.match(r'^[a-zA-Z0-9_\-]+$', file_id):
        return False, "File ID contains invalid characters"

    return True, None


# ====================
# Git/Branch Validation
# ====================

def validate_git_branch_name(branch: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Git branch name is safe.

    Returns:
        (is_valid, error_message)
    """
    # Git branch name restrictions
    if not branch:
        return False, "Branch name cannot be empty"

    # Check for dangerous characters
    dangerous = ['..', '~', '^', ':', '?', '*', '[', '\\', ' ', '\0']
    for char in dangerous:
        if char in branch:
            return False, f"Branch name contains invalid character: '{char}'"

    # Cannot start or end with /
    if branch.startswith('/') or branch.endswith('/'):
        return False, "Branch name cannot start or end with /"

    # Cannot contain consecutive slashes
    if '//' in branch:
        return False, "Branch name cannot contain consecutive slashes"

    # Valid pattern
    if not re.match(r'^[a-zA-Z0-9_\-/]+$', branch):
        return False, "Branch name contains invalid characters"

    return True, None


# ====================
# Comprehensive Input Validator
# ====================

def validate_user_input(
    text: str,
    check_sql: bool = True,
    check_xss: bool = True,
    check_path_traversal: bool = True,
    min_length: int = 0,
    max_length: int = 10000
) -> Tuple[bool, List[str]]:
    """
    Run comprehensive validation checks on user input.

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    # Length check
    is_valid, error = validate_length(text, min_length, max_length)
    if not is_valid:
        errors.append(error)

    # Security checks
    if check_sql:
        is_suspicious, pattern = detect_sql_injection(text)
        if is_suspicious:
            errors.append(f"Potential SQL injection detected: {pattern}")

    if check_xss:
        is_suspicious, pattern = detect_xss(text)
        if is_suspicious:
            errors.append(f"Potential XSS detected: {pattern}")

    if check_path_traversal:
        is_suspicious, pattern = detect_path_traversal(text)
        if is_suspicious:
            errors.append(f"Potential path traversal detected: {pattern}")

    return len(errors) == 0, errors


# ====================
# Validation Decorator
# ====================

def validate_input(**validation_rules):
    """
    Decorator for validating function inputs.

    Example:
        @validate_input(username={'min_length': 3, 'max_length': 50})
        def create_user(username: str):
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get function parameter names
            import inspect
            sig = inspect.signature(func)
            params = sig.parameters

            # Map args to parameter names
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Validate each parameter
            for param_name, rules in validation_rules.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]

                    # String length validation
                    if isinstance(value, str):
                        min_len = rules.get('min_length', 0)
                        max_len = rules.get('max_length', 10000)
                        is_valid, error = validate_length(value, min_len, max_len)
                        if not is_valid:
                            raise ValueError(f"Parameter '{param_name}': {error}")

                    # Numeric bounds validation
                    if isinstance(value, (int, float)):
                        min_val = rules.get('min_value')
                        max_val = rules.get('max_value')
                        is_valid, error = validate_numeric_bounds(value, min_val, max_val)
                        if not is_valid:
                            raise ValueError(f"Parameter '{param_name}': {error}")

            return func(*args, **kwargs)
        return wrapper
    return decorator


# Export all validators
__all__ = [
    # Security detection
    'detect_sql_injection', 'detect_xss', 'detect_path_traversal',
    # String validation
    'validate_length', 'validate_alphanumeric', 'validate_no_special_chars',
    # Numeric validation
    'validate_numeric_bounds', 'validate_positive', 'validate_non_negative',
    # File validation
    'validate_filename', 'validate_file_size', 'validate_mime_type',
    # URL validation
    'validate_url', 'validate_domain',
    # Telegram validation
    'validate_telegram_user_id', 'validate_telegram_file_id',
    # Git validation
    'validate_git_branch_name',
    # Comprehensive
    'validate_user_input',
    # Decorator
    'validate_input'
]
