"""
Tests for SEC-008: Insecure Deserialization Prevention
"""

import pytest
import json
import tempfile
import os
from secure_deserializer import (
    SecureDeserializer,
    DeserializationError,
    safe_json_loads,
    safe_json_load,
    validate_dict,
    validate_list,
    create_schema_validator,
    create_type_validator
)


class TestSecureDeserializer:
    """Test suite for SecureDeserializer"""

    def test_basic_deserialization(self):
        """Test basic JSON deserialization works"""
        deserializer = SecureDeserializer()
        data = {"key": "value", "number": 42}
        json_string = json.dumps(data)

        result = deserializer.safe_json_loads(json_string)
        assert result == data

    def test_size_limit_enforcement(self):
        """Test that size limits are enforced"""
        deserializer = SecureDeserializer()

        # Create a large JSON string
        large_data = {"key": "x" * 1000000}
        json_string = json.dumps(large_data)

        # Should fail with small max_size
        with pytest.raises(DeserializationError, match="JSON too large"):
            deserializer.safe_json_loads(json_string, max_size=100)

    def test_invalid_json_handling(self):
        """Test that invalid JSON is rejected"""
        deserializer = SecureDeserializer()

        invalid_json = "{ invalid json }"

        with pytest.raises(DeserializationError, match="Invalid JSON"):
            deserializer.safe_json_loads(invalid_json)

    def test_depth_limit_enforcement(self):
        """Test that nesting depth limits are enforced"""
        deserializer = SecureDeserializer()

        # Create deeply nested structure
        deep_data = {"level": 1}
        current = deep_data
        for i in range(2, 20):
            current["nested"] = {"level": i}
            current = current["nested"]

        json_string = json.dumps(deep_data)

        with pytest.raises(DeserializationError, match="nesting too deep"):
            deserializer.safe_json_loads(json_string)

    def test_schema_validation_success(self):
        """Test successful schema validation"""
        deserializer = SecureDeserializer()

        data = {"name": "test", "value": 42}
        json_string = json.dumps(data)

        schema = create_schema_validator(["name", "value"])
        result = deserializer.safe_json_loads(json_string, schema=schema)

        assert result == data

    def test_schema_validation_failure(self):
        """Test schema validation rejection"""
        deserializer = SecureDeserializer()

        data = {"name": "test"}  # Missing "value" key
        json_string = json.dumps(data)

        schema = create_schema_validator(["name", "value"])

        with pytest.raises(DeserializationError, match="does not match expected schema"):
            deserializer.safe_json_loads(json_string, schema=schema)

    def test_hmac_integrity_check(self):
        """Test HMAC integrity verification"""
        secret = "test-secret-key"
        deserializer = SecureDeserializer(secret_key=secret)

        data = {"test": "data"}
        json_string, signature = deserializer.create_signed_json(data)

        # Should succeed with correct signature
        result = deserializer.safe_json_loads(
            json_string,
            verify_integrity=True,
            hmac_signature=signature
        )
        assert result == data

    def test_hmac_tamper_detection(self):
        """Test that tampered data is detected"""
        secret = "test-secret-key"
        deserializer = SecureDeserializer(secret_key=secret)

        data = {"test": "data"}
        json_string, signature = deserializer.create_signed_json(data)

        # Tamper with the data
        tampered_json = json_string.replace("data", "hacked")

        # Should fail integrity check
        with pytest.raises(DeserializationError, match="Integrity verification failed"):
            deserializer.safe_json_loads(
                tampered_json,
                verify_integrity=True,
                hmac_signature=signature
            )

    def test_file_loading(self):
        """Test safe file loading"""
        deserializer = SecureDeserializer()

        data = {"file": "test", "number": 123}

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            result = deserializer.safe_json_load(temp_path)
            assert result == data
        finally:
            os.unlink(temp_path)

    def test_file_not_found(self):
        """Test handling of missing files"""
        deserializer = SecureDeserializer()

        with pytest.raises(DeserializationError, match="File not found"):
            deserializer.safe_json_load("/nonexistent/path.json")

    def test_convenience_functions(self):
        """Test convenience wrapper functions"""
        data = {"test": "convenience"}
        json_string = json.dumps(data)

        # Test safe_json_loads
        result = safe_json_loads(json_string)
        assert result == data

        # Test with schema
        schema = validate_dict
        result = safe_json_loads(json_string, schema=schema)
        assert result == data

    def test_type_validators(self):
        """Test built-in type validators"""
        # Test validate_dict
        assert validate_dict({"key": "value"}) is True
        assert validate_dict([1, 2, 3]) is False

        # Test validate_list
        assert validate_list([1, 2, 3]) is True
        assert validate_list({"key": "value"}) is False

        # Test create_type_validator
        validator = create_type_validator(str)
        assert validator("test") is True
        assert validator(123) is False

    def test_array_depth_check(self):
        """Test depth checking works for arrays too"""
        deserializer = SecureDeserializer()

        # Create deeply nested array
        deep_array = [1]
        for _ in range(15):
            deep_array = [deep_array]

        json_string = json.dumps(deep_array)

        with pytest.raises(DeserializationError, match="nesting too deep"):
            deserializer.safe_json_loads(json_string)

    def test_no_pickle_allowed(self):
        """Verify pickle is NOT used (documentation test)"""
        # This project should use JSON only
        # Verify no pickle imports in secure_deserializer.py
        with open('secure_deserializer.py', 'r') as f:
            content = f.read()

        assert 'import pickle' not in content
        assert 'import marshal' not in content
        assert 'from pickle' not in content

    def test_serialization_error_handling(self):
        """Test that non-serializable objects are rejected"""
        deserializer = SecureDeserializer(secret_key="test")

        # Non-serializable object
        class CustomClass:
            pass

        obj = CustomClass()

        with pytest.raises(DeserializationError, match="Serialization failed"):
            deserializer.create_signed_json(obj)

    def test_integrity_without_key(self):
        """Test that integrity check requires secret key"""
        deserializer = SecureDeserializer()  # No secret key

        data = {"test": "data"}
        json_string = json.dumps(data)

        with pytest.raises(DeserializationError, match="no secret key"):
            deserializer.safe_json_loads(
                json_string,
                verify_integrity=True,
                hmac_signature="dummy"
            )

    def test_integrity_without_signature(self):
        """Test that integrity check requires signature"""
        deserializer = SecureDeserializer(secret_key="test")

        data = {"test": "data"}
        json_string = json.dumps(data)

        with pytest.raises(DeserializationError, match="no HMAC signature"):
            deserializer.safe_json_loads(
                json_string,
                verify_integrity=True
            )

    def test_complex_schema_validation(self):
        """Test complex custom schema validator"""
        deserializer = SecureDeserializer()

        # Custom validator: must be dict with "id" as int and "name" as string
        def complex_schema(data):
            if not isinstance(data, dict):
                return False
            if "id" not in data or not isinstance(data["id"], int):
                return False
            if "name" not in data or not isinstance(data["name"], str):
                return False
            return True

        # Valid data
        valid_data = {"id": 1, "name": "test"}
        result = deserializer.safe_json_loads(json.dumps(valid_data), schema=complex_schema)
        assert result == valid_data

        # Invalid data (wrong type for id)
        invalid_data = {"id": "wrong", "name": "test"}
        with pytest.raises(DeserializationError):
            deserializer.safe_json_loads(json.dumps(invalid_data), schema=complex_schema)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
