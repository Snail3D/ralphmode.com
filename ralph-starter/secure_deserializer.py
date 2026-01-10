"""
SEC-008: Insecure Deserialization Prevention

This module provides secure deserialization utilities to prevent deserialization attacks.
- No pickle/marshal on untrusted data
- JSON-only for serialization
- Schema validation before deserialization
- Integrity checks on serialized data
- Error logging and monitoring
"""

import json
import hashlib
import hmac
from typing import Any, Dict, Optional, Callable
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)


class DeserializationError(Exception):
    """Raised when deserialization fails validation"""
    pass


class SecureDeserializer:
    """
    Secure JSON deserializer with validation and integrity checks.

    Features:
    - Schema validation
    - Size limits
    - Type checking
    - Integrity verification with HMAC
    - Comprehensive error logging
    """

    # Maximum size for JSON strings (10MB default)
    MAX_JSON_SIZE = 10 * 1024 * 1024

    # Maximum depth for nested structures
    MAX_DEPTH = 10

    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize secure deserializer.

        Args:
            secret_key: Optional secret key for HMAC integrity checks
        """
        self.secret_key = secret_key

    def safe_json_loads(
        self,
        json_string: str,
        schema: Optional[Callable[[Any], bool]] = None,
        max_size: Optional[int] = None,
        verify_integrity: bool = False,
        hmac_signature: Optional[str] = None
    ) -> Any:
        """
        Safely deserialize JSON with validation.

        Args:
            json_string: JSON string to deserialize
            schema: Optional validation function that returns True if valid
            max_size: Maximum allowed size in bytes (default: MAX_JSON_SIZE)
            verify_integrity: Whether to verify HMAC signature
            hmac_signature: HMAC signature to verify against

        Returns:
            Deserialized Python object

        Raises:
            DeserializationError: If validation fails
        """
        try:
            # 1. Size check
            max_allowed = max_size or self.MAX_JSON_SIZE
            if len(json_string) > max_allowed:
                logger.warning(
                    f"JSON size {len(json_string)} exceeds limit {max_allowed}",
                    extra={'event': 'deserialization_size_exceeded'}
                )
                raise DeserializationError(
                    f"JSON too large: {len(json_string)} bytes (max: {max_allowed})"
                )

            # 2. Integrity check (if enabled)
            if verify_integrity:
                if not self.secret_key:
                    raise DeserializationError("Integrity check requested but no secret key configured")
                if not hmac_signature:
                    raise DeserializationError("Integrity check requested but no HMAC signature provided")

                if not self._verify_hmac(json_string, hmac_signature):
                    logger.error(
                        "HMAC verification failed",
                        extra={'event': 'deserialization_integrity_failed'}
                    )
                    raise DeserializationError("Integrity verification failed")

            # 3. Parse JSON
            try:
                data = json.loads(json_string)
            except json.JSONDecodeError as e:
                logger.error(
                    f"JSON parse error: {e}",
                    extra={'event': 'deserialization_parse_error', 'error': str(e)}
                )
                raise DeserializationError(f"Invalid JSON: {e}")

            # 4. Depth check
            if not self._check_depth(data, self.MAX_DEPTH):
                logger.warning(
                    f"JSON depth exceeds limit {self.MAX_DEPTH}",
                    extra={'event': 'deserialization_depth_exceeded'}
                )
                raise DeserializationError(f"JSON nesting too deep (max: {self.MAX_DEPTH})")

            # 5. Schema validation (if provided)
            if schema:
                try:
                    if not schema(data):
                        logger.warning(
                            "Schema validation failed",
                            extra={'event': 'deserialization_schema_invalid'}
                        )
                        raise DeserializationError("Data does not match expected schema")
                except Exception as e:
                    logger.error(
                        f"Schema validation error: {e}",
                        extra={'event': 'deserialization_schema_error', 'error': str(e)}
                    )
                    raise DeserializationError(f"Schema validation error: {e}")

            logger.debug(
                "Successful deserialization",
                extra={'event': 'deserialization_success', 'size': len(json_string)}
            )

            return data

        except DeserializationError:
            # Re-raise our custom errors
            raise
        except Exception as e:
            # Catch-all for unexpected errors
            logger.error(
                f"Unexpected deserialization error: {e}",
                extra={'event': 'deserialization_unexpected_error', 'error': str(e)}
            )
            raise DeserializationError(f"Deserialization failed: {e}")

    def safe_json_load(
        self,
        file_path: str,
        schema: Optional[Callable[[Any], bool]] = None,
        max_size: Optional[int] = None
    ) -> Any:
        """
        Safely load and deserialize JSON from a file.

        Args:
            file_path: Path to JSON file
            schema: Optional validation function
            max_size: Maximum allowed file size

        Returns:
            Deserialized Python object

        Raises:
            DeserializationError: If validation fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_string = f.read()

            return self.safe_json_loads(
                json_string,
                schema=schema,
                max_size=max_size
            )

        except FileNotFoundError as e:
            logger.error(
                f"File not found: {file_path}",
                extra={'event': 'deserialization_file_not_found', 'path': file_path}
            )
            raise DeserializationError(f"File not found: {file_path}")
        except IOError as e:
            logger.error(
                f"IO error reading file: {e}",
                extra={'event': 'deserialization_io_error', 'error': str(e)}
            )
            raise DeserializationError(f"Failed to read file: {e}")

    def create_signed_json(self, data: Any) -> tuple[str, str]:
        """
        Serialize data to JSON with HMAC signature for integrity.

        Args:
            data: Python object to serialize

        Returns:
            Tuple of (json_string, hmac_signature)

        Raises:
            DeserializationError: If serialization fails
        """
        if not self.secret_key:
            raise DeserializationError("Cannot create signed JSON without secret key")

        try:
            json_string = json.dumps(data)
            signature = self._create_hmac(json_string)
            return json_string, signature

        except (TypeError, ValueError) as e:
            logger.error(
                f"JSON serialization error: {e}",
                extra={'event': 'serialization_error', 'error': str(e)}
            )
            raise DeserializationError(f"Serialization failed: {e}")

    def _create_hmac(self, data: str) -> str:
        """Create HMAC-SHA256 signature for data"""
        return hmac.new(
            self.secret_key.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _verify_hmac(self, data: str, signature: str) -> bool:
        """Verify HMAC-SHA256 signature"""
        expected = self._create_hmac(data)
        return hmac.compare_digest(expected, signature)

    def _check_depth(self, obj: Any, max_depth: int, current_depth: int = 0) -> bool:
        """
        Recursively check nesting depth of data structures.

        Args:
            obj: Object to check
            max_depth: Maximum allowed depth
            current_depth: Current recursion depth

        Returns:
            True if within depth limit, False otherwise
        """
        if current_depth > max_depth:
            return False

        if isinstance(obj, dict):
            return all(
                self._check_depth(v, max_depth, current_depth + 1)
                for v in obj.values()
            )
        elif isinstance(obj, list):
            return all(
                self._check_depth(item, max_depth, current_depth + 1)
                for item in obj
            )
        else:
            # Primitive types don't add depth
            return True


# Common schema validators
def validate_dict(data: Any) -> bool:
    """Validate that data is a dictionary"""
    return isinstance(data, dict)


def validate_list(data: Any) -> bool:
    """Validate that data is a list"""
    return isinstance(data, list)


def create_schema_validator(required_keys: list[str]) -> Callable[[Any], bool]:
    """
    Create a validator that checks for required dictionary keys.

    Args:
        required_keys: List of required key names

    Returns:
        Validation function
    """
    def validator(data: Any) -> bool:
        if not isinstance(data, dict):
            return False
        return all(key in data for key in required_keys)

    return validator


def create_type_validator(expected_type: type) -> Callable[[Any], bool]:
    """
    Create a validator that checks object type.

    Args:
        expected_type: Expected Python type

    Returns:
        Validation function
    """
    def validator(data: Any) -> bool:
        return isinstance(data, expected_type)

    return validator


# Global instance for convenience (no integrity checks by default)
default_deserializer = SecureDeserializer()


# Convenience functions
def safe_json_loads(
    json_string: str,
    schema: Optional[Callable[[Any], bool]] = None,
    max_size: Optional[int] = None
) -> Any:
    """
    Convenience function for safe JSON deserialization.
    Uses global default deserializer without integrity checks.
    """
    return default_deserializer.safe_json_loads(
        json_string,
        schema=schema,
        max_size=max_size
    )


def safe_json_load(
    file_path: str,
    schema: Optional[Callable[[Any], bool]] = None,
    max_size: Optional[int] = None
) -> Any:
    """
    Convenience function for safe JSON file loading.
    Uses global default deserializer.
    """
    return default_deserializer.safe_json_load(
        file_path,
        schema=schema,
        max_size=max_size
    )
