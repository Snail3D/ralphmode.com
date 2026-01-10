# SEC-007: Security Misconfiguration Prevention

This document describes the security configuration system implemented for Ralph Mode.

## Overview

SEC-007 implements comprehensive security configuration validation to prevent common misconfigurations that could lead to vulnerabilities in production.

## Features

### 1. Environment-Specific Configuration

Three environments are supported:
- **Development**: Permissive settings for local development
- **Staging**: Production-like with some debug capabilities
- **Production**: Strictest security enforcement

Set via `RALPH_ENV` environment variable (defaults to `production` for safety).

### 2. Automated Configuration Scanning

The `config.py` module validates configuration on startup and prevents the server from starting with insecure settings.

Checks include:
- ✅ DEBUG=False in production
- ✅ Secret keys set and sufficiently long (min 32 chars)
- ✅ No default/insecure credentials (e.g., "changeme", "password123")
- ✅ HTTPS enforced in production
- ✅ Secure cookie settings (Secure, HttpOnly, SameSite)
- ✅ Unnecessary features disabled (template auto-reload, etc.)
- ✅ Testing mode disabled in production
- ✅ CORS origins properly configured
- ✅ API keys present
- ✅ No localhost in production ALLOWED_ORIGINS

### 3. Security Headers (nginx.conf)

Already implemented in nginx configuration:
- `X-Frame-Options: DENY` - Prevents clickjacking
- `X-Content-Type-Options: nosniff` - Prevents MIME sniffing
- `X-XSS-Protection: 1; mode=block` - XSS filter
- `Referrer-Policy: strict-origin-when-cross-origin` - Controls referrer info
- `Permissions-Policy` - Restricts browser features
- `server_tokens off` - Hides nginx version

### 4. Error Handling Without Information Leakage

Error handlers in `api_server.py` prevent stack trace leakage:
- 403 errors: Generic "Forbidden" message
- 500 errors: Generic "Internal Server Error" message
- Detailed errors logged but not exposed to clients

### 5. Directory Listing Disabled

Nginx configuration includes `autoindex off` to prevent directory browsing.

## Usage

### Running Configuration Validation

```bash
# Validate current environment
python config.py

# Validate specific environment
RALPH_ENV=production python config.py

# Run tests
python test_config.py
```

### Starting the API Server

The API server automatically validates configuration on startup:

```bash
# Development (permissive)
RALPH_ENV=development python api_server.py

# Production (strict)
RALPH_ENV=production python api_server.py
```

If critical security issues are found, the server will refuse to start:

```
🚨 SECURITY CONFIGURATION ERRORS DETECTED 🚨

  ❌ CRITICAL: DEBUG=True in production environment
  ❌ CRITICAL: SECRET_KEY not set in production

❌ Server cannot start with insecure configuration
   Fix the above issues and try again.
```

### Setting Up Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Generate secure secret keys:
   ```bash
   python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" >> .env
   python -c "import secrets; print('SESSION_SECRET_KEY=' + secrets.token_hex(32))" >> .env
   python -c "import secrets; print('CSRF_SECRET_KEY=' + secrets.token_hex(32))" >> .env
   ```

3. Fill in other required values (API keys, etc.)

4. Set environment to production:
   ```bash
   echo "RALPH_ENV=production" >> .env
   ```

## Production Deployment Checklist

Before deploying to production, ensure:

- [ ] `RALPH_ENV=production` is set
- [ ] `DEBUG=False` (automatic in production)
- [ ] All secret keys are set with random 64+ character values
- [ ] `FORCE_HTTPS=True` is set
- [ ] `ALLOWED_ORIGINS` contains only production domains
- [ ] No localhost URLs in ALLOWED_ORIGINS
- [ ] All required API keys are set (TELEGRAM_BOT_TOKEN, GROQ_API_KEY)
- [ ] Nginx is configured with SSL certificates
- [ ] Server is behind a reverse proxy (nginx)
- [ ] Configuration validation passes: `python config.py`
- [ ] All tests pass: `python test_config.py`

## Configuration Reference

### Critical Settings (Production)

| Setting | Required | Description |
|---------|----------|-------------|
| `RALPH_ENV` | Yes | Must be "production" |
| `DEBUG` | Yes | Must be False |
| `SECRET_KEY` | Yes | Min 32 chars, no defaults |
| `SESSION_SECRET_KEY` | Yes | Min 32 chars, no defaults |
| `CSRF_SECRET_KEY` | Yes | Min 32 chars, no defaults |
| `FORCE_HTTPS` | Yes | Must be True |
| `ALLOWED_ORIGINS` | Yes | Whitelist of allowed origins |
| `SESSION_COOKIE_SECURE` | Yes | Must be True |

### Forbidden Values

The system detects and rejects these insecure defaults:
- changeme
- password / password123
- admin
- secret
- default
- your_token_here / your_key_here / your_password_here
- test / demo
- 12345

## Testing

Run the comprehensive test suite:

```bash
python test_config.py
```

Tests cover:
- Debug mode enforcement
- Secret key validation
- Default credential detection
- HTTPS enforcement
- Secure cookie configuration
- Unnecessary feature detection
- API key validation
- CORS configuration
- Environment-specific rules

## Integration with Other Security Layers

SEC-007 complements other security implementations:

- **SEC-003 (CSRF Protection)**: Uses CSRF_SECRET_KEY from config
- **SEC-004 (Authentication)**: Uses SESSION_SECRET_KEY from config
- **SEC-005 (Data Protection)**: Enforces HTTPS and secure cookies
- **SEC-006 (Access Control)**: Uses SECRET_KEY for JWT signing

## Troubleshooting

### "Server cannot start with insecure configuration"

Check the error messages and fix the reported issues. Common problems:
- Missing or short secret keys
- DEBUG=True in production
- Default credentials not changed

### "SECRET_KEY not set in production"

Generate and set a secure secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Add to `.env`:
```
SECRET_KEY=<generated_value>
```

### Warnings vs Critical Issues

- **CRITICAL**: Server will not start (security risk)
- **WARNING**: Server will start but configuration should be improved
- **ERROR**: Functionality may be impaired (e.g., missing API keys)

## Security Best Practices

1. **Never commit .env files** - They contain secrets
2. **Use environment variables in production** - Don't hardcode secrets
3. **Rotate secrets regularly** - Especially after team member changes
4. **Run validation before deployment** - Catch issues early
5. **Monitor configuration drift** - Set up alerts for config changes
6. **Use different secrets per environment** - Dev/staging/prod should differ

## References

- OWASP Top 10 2021: A05 Security Misconfiguration
- [OWASP Security Misconfiguration](https://owasp.org/Top10/A05_2021-Security_Misconfiguration/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)
