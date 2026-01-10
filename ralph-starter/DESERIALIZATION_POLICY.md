# Secure Deserialization Policy (SEC-008)

## Overview

This project implements strict deserialization security to prevent **insecure deserialization attacks** (OWASP Top 10: A08).

## Policy Rules

### ✅ ALLOWED

1. **JSON Only** - Use JSON for all serialization/deserialization
   - JSON is a data format, not code
   - Cannot execute arbitrary code during parsing
   - Human-readable and widely supported

2. **Secure Deserializer** - Always use `secure_deserializer.py` module
   ```python
   from secure_deserializer import safe_json_loads, safe_json_load

   # Load JSON string with validation
   data = safe_json_loads(json_string)

   # Load JSON file with validation
   data = safe_json_load("/path/to/file.json")
   ```

3. **Schema Validation** - Validate data structure when needed
   ```python
   from secure_deserializer import safe_json_loads, create_schema_validator

   # Require specific keys
   schema = create_schema_validator(["id", "name", "email"])
   data = safe_json_loads(json_string, schema=schema)
   ```

### ❌ PROHIBITED

1. **NO pickle** - Never use `pickle` or `marshal` on untrusted data
   - Can execute arbitrary code
   - Major security vulnerability
   - Use JSON instead

2. **NO unsafe YAML** - Avoid `yaml.load()` (use `yaml.safe_load()` if needed)
   - YAML can execute Python code
   - Prefer JSON over YAML

3. **NO eval/exec** - Never deserialize code
   - `eval()`
   - `exec()`
   - `compile()`
   - Use JSON for data only

## Features of Secure Deserializer

### 1. Size Limits
```python
# Prevent DoS via huge payloads
data = safe_json_loads(json_string, max_size=1024*1024)  # 1MB limit
```

### 2. Depth Limits
- Maximum nesting depth: 10 levels
- Prevents stack overflow attacks
- Automatically checked

### 3. Schema Validation
```python
# Custom validation function
def validate_user(data):
    return (
        isinstance(data, dict) and
        "user_id" in data and
        isinstance(data["user_id"], str)
    )

user = safe_json_loads(json_string, schema=validate_user)
```

### 4. Integrity Checks (HMAC)
```python
# For tamper-proof data
deserializer = SecureDeserializer(secret_key="your-secret")

# Create signed JSON
json_str, signature = deserializer.create_signed_json(data)

# Verify on load
verified_data = deserializer.safe_json_loads(
    json_str,
    verify_integrity=True,
    hmac_signature=signature
)
```

### 5. Comprehensive Logging
- All deserialization errors logged
- Monitoring for attack patterns
- Audit trail for security review

## Common Patterns

### Loading Config Files
```python
from secure_deserializer import safe_json_load

config = safe_json_load("config.json")
```

### API Request Handling
```python
from secure_deserializer import safe_json_loads, create_schema_validator

# Define expected schema
api_schema = create_schema_validator(["action", "user_id"])

# Parse and validate
request_data = safe_json_loads(
    request.body,
    schema=api_schema,
    max_size=100_000  # 100KB limit for API requests
)
```

### Log File Parsing
```python
from secure_deserializer import safe_json_loads

with open("app.log", "r") as f:
    for line in f:
        try:
            log_entry = safe_json_loads(line.strip())
            process_log(log_entry)
        except DeserializationError as e:
            # Log corrupted entry but continue
            logger.warning(f"Invalid log entry: {e}")
```

## Migration Guide

### Before (Unsafe)
```python
import json
import pickle

# ❌ Unsafe - can execute code
user = pickle.loads(untrusted_data)

# ❌ No validation
config = json.loads(request.body)
```

### After (Secure)
```python
from secure_deserializer import safe_json_loads, create_schema_validator

# ✅ JSON only, no code execution
config = safe_json_loads(request.body)

# ✅ With validation
schema = create_schema_validator(["username", "email"])
user = safe_json_loads(user_json, schema=schema)
```

## Testing

Run the test suite to verify deserialization security:

```bash
pytest test_secure_deserializer.py -v
```

Tests cover:
- ✅ Size limit enforcement
- ✅ Depth limit enforcement
- ✅ Invalid JSON rejection
- ✅ Schema validation
- ✅ HMAC integrity checks
- ✅ Tamper detection
- ✅ Error handling
- ✅ No pickle/marshal usage

## Security Benefits

1. **Code Execution Prevention** - JSON cannot run code
2. **DoS Protection** - Size and depth limits prevent resource exhaustion
3. **Data Validation** - Schema checks ensure data integrity
4. **Tamper Detection** - HMAC signatures detect modifications
5. **Audit Trail** - All errors logged for security monitoring
6. **Defense in Depth** - Multiple layers of protection

## References

- OWASP Top 10 2021: A08 - Software and Data Integrity Failures
- CWE-502: Deserialization of Untrusted Data
- OWASP Deserialization Cheat Sheet

## Questions?

Contact the security team or review `secure_deserializer.py` source code for implementation details.
