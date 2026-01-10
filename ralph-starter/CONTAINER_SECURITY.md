# Container Security (SEC-017)

This document outlines the container security measures implemented for Ralph Mode Bot.

## Security Features Implemented

### 1. Minimal Base Images
- **Build stage**: Python 3.11 slim (reduces attack surface)
- **Final stage**: Python 3.11 slim (distroless-like approach)
- Multi-stage build removes build tools from final image
- Only runtime dependencies in final image

### 2. Non-Root User (UID 1000+)
- Container runs as user `ralph` (UID 1000, GID 1000)
- No root privileges inside container
- All files owned by non-root user
- Shell disabled (`/sbin/nologin`) for security

### 3. Read-Only Root Filesystem
- Container filesystem is read-only by default
- Write operations only to mounted tmpfs/volumes:
  - `/tmp` - temporary files (100MB limit)
  - `/app/logs` - application logs (500MB limit)
  - `/app/data` - persistent data (volume-mounted)

### 4. No Privileged Containers
- `privileged: false` explicitly set
- Prevents host kernel access
- Limits container escape vectors

### 5. Capability Dropping
- All Linux capabilities dropped: `cap_drop: ALL`
- No special privileges retained
- Follows principle of least privilege

### 6. No Sensitive Data in Image Layers
- `.dockerignore` prevents secrets in build context
- `.env` files excluded from image
- Keys and certificates excluded
- Build history doesn't contain secrets

### 7. Image Signing and Verification
- Cosign support configured in CI/CD
- Ready for signing when container registry is set up
- Verification workflow in place

### 8. Container Scanning in CI/CD
- **Trivy**: Vulnerability scanning
- **Grype**: Additional vulnerability detection
- **Hadolint**: Dockerfile best practices
- **ggshield**: Secret detection in layers
- **Docker Bench**: Configuration audit
- **Syft**: SBOM generation
- Weekly scheduled scans

## Resource Limits

### Ralph Bot Container
- **CPU Limit**: 2.0 cores
- **Memory Limit**: 2GB
- **CPU Reserved**: 0.5 cores
- **Memory Reserved**: 512MB

### Redis Container
- **CPU Limit**: 1.0 core
- **Memory Limit**: 512MB
- **CPU Reserved**: 0.25 cores
- **Memory Reserved**: 128MB

## Network Security

- Isolated bridge network (`ralph-network`)
- Custom subnet: 172.28.0.0/16
- No host network access
- Services communicate only within network

## Logging Configuration

- JSON file driver with rotation
- Max log size: 10MB (bot), 5MB (Redis)
- Max files: 3 (bot), 2 (Redis)
- Prevents disk exhaustion

## Health Checks

### Ralph Bot
- Interval: 30 seconds
- Timeout: 10 seconds
- Retries: 3
- Start period: 5 seconds

### Redis
- Command: `redis-cli ping`
- Interval: 30 seconds
- Timeout: 5 seconds
- Retries: 3

## Additional Security Options

- `no-new-privileges:true` - Prevents privilege escalation
- `noexec,nosuid,nodev` on tmpfs mounts
- Environment isolation
- Secret management via environment variables

## Usage

### Build the image
```bash
docker-compose build
```

### Run with security hardening
```bash
docker-compose up -d
```

### View security scan results
```bash
# Scan image with Trivy
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image ralph-bot:latest

# Scan with Grype
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  anchore/grype ralph-bot:latest
```

### Verify configuration
```bash
# Check running as non-root
docker-compose exec ralph-bot whoami
# Should output: ralph

# Check capabilities
docker inspect ralph-bot | jq '.[0].HostConfig.CapDrop'
# Should show: ["ALL"]

# Check read-only filesystem
docker inspect ralph-bot | jq '.[0].HostConfig.ReadonlyRootfs'
# Should show: true
```

## Production Deployment

### Before Deploying to Production

1. **Set up container registry** (Docker Hub, GitHub Container Registry, etc.)
2. **Generate signing keys** for Cosign
3. **Configure image signing** in CI/CD
4. **Set up secrets manager** (AWS Secrets Manager, HashiCorp Vault)
5. **Enable automated scanning** with alerts
6. **Configure log aggregation** (ELK, Splunk, Datadog)

### Production Environment Variables

Create a `.env.production` file with:
```bash
# Bot configuration
TELEGRAM_BOT_TOKEN=<from secrets manager>
GROQ_API_KEY=<from secrets manager>

# Redis
REDIS_PASSWORD=<strong random password>
REDIS_HOST=redis
REDIS_PORT=6379

# Security
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Deploy to Production
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Monitoring and Alerting

- Monitor container resource usage
- Alert on health check failures
- Alert on security scan findings
- Track vulnerability remediation
- Audit container logs regularly

## Compliance

This implementation addresses:
- **CIS Docker Benchmark**: Best practices for container security
- **OWASP Container Security**: Top 10 container risks
- **PCI-DSS**: Payment card industry requirements
- **GDPR**: Data protection compliance
- **SOC 2**: Security and availability controls

## References

- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [OWASP Container Security](https://owasp.org/www-project-docker-top-10/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [Trivy Documentation](https://trivy.dev/)
- [Cosign Documentation](https://docs.sigstore.dev/cosign/overview/)
