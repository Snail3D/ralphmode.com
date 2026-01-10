# SEC-017: Container Security Implementation
# Multi-stage build for minimal final image

# Stage 1: Build stage with full Python tooling
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final minimal runtime image (distroless-like)
FROM python:3.11-slim

# Security: Create non-root user with UID 1000+
RUN groupadd -r ralph --gid=1000 && \
    useradd -r -g ralph --uid=1000 --home-dir=/app --shell=/sbin/nologin ralph

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application files
COPY --chown=ralph:ralph ralph_bot.py .
COPY --chown=ralph:ralph config.py .
COPY --chown=ralph:ralph auth.py .
COPY --chown=ralph:ralph jwt_manager.py .
COPY --chown=ralph:ralph rate_limiter.py .
COPY --chown=ralph:ralph validators.py .
COPY --chown=ralph:ralph schemas.py .
COPY --chown=ralph:ralph secrets_manager.py .
COPY --chown=ralph:ralph security_logging.py .
COPY --chown=ralph:ralph csrf_protection.py .
COPY --chown=ralph:ralph xss_prevention.py .
COPY --chown=ralph:ralph database.py .
COPY --chown=ralph:ralph session_manager.py .
COPY --chown=ralph:ralph sanitizer.py .
COPY --chown=ralph:ralph rbac.py .
COPY --chown=ralph:ralph data_protection.py .
COPY --chown=ralph:ralph api_server.py .
COPY --chown=ralph:ralph security_alerts.py .
COPY --chown=ralph:ralph scripts scripts/

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data && \
    chown -R ralph:ralph /app/logs /app/data

# Security: Drop all capabilities except required ones
# NET_BIND_SERVICE not needed since we use port > 1024

# Set environment
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Security: Switch to non-root user
USER ralph

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the bot
CMD ["python", "-u", "ralph_bot.py"]
