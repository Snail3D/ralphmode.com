# GitHub Actions Workflows

## Security Workflows

### security.yml (SEC-023)
**Comprehensive Security Scanning Pipeline**

Automated security testing with SAST, DAST, SCA, secrets detection, and container scanning.

**Triggers**:
- Pull requests to main/develop
- Push to main/develop
- Weekly schedule (Sunday 2 AM UTC)
- Manual dispatch

**Key Features**:
- 11 different security scanning tools
- SARIF integration with GitHub Security
- Critical findings fail the build
- Weekly comprehensive reports
- Automatic issue creation for findings

**Tools**:
- SAST: Semgrep, CodeQL, Bandit
- SCA: Snyk, Dependabot, Safety
- Secrets: GitLeaks, TruffleHog
- Container: Trivy, Grype
- DAST: OWASP ZAP
- Compliance: License checking

See [SECURITY_SCANNING.md](../../SECURITY_SCANNING.md) for complete documentation.

### container-security.yml (SEC-017)
**Container Image Security**

Scans Docker images for vulnerabilities, misconfigurations, and secrets.

**Features**:
- Dockerfile linting (Hadolint)
- Vulnerability scanning (Trivy, Grype)
- Secret detection (GitGuardian)
- SBOM generation (Syft)
- Configuration audit
- Image signing support (Cosign)

### security-tests.yml (SEC-003)
**CSRF Protection Tests**

Validates CSRF protection implementation in the API server.

**Tests**:
- Token generation/validation
- Origin validation
- Double-submit cookie pattern
- Session security
- Failure scenarios

## Usage

### Viewing Results

**Security Tab**:
```
Repository → Security → Code scanning alerts
```

**Workflow Runs**:
```
Actions → Select workflow → View run details
```

**Artifacts**:
- Download from workflow run page
- Contains detailed reports (JSON, Markdown)

### Required Secrets

Configure in: `Settings → Secrets and variables → Actions`

**Required**:
- `SNYK_TOKEN` - Get from https://snyk.io

**Optional**:
- `GITGUARDIAN_API_KEY` - For enhanced secret scanning

### Local Testing

Before pushing, run scans locally:

```bash
# Install tools
pip install bandit safety

# Run scans
bandit -r . -f screen
safety check --file requirements.txt
```

### Build Failures

If security gate fails:

1. Check Actions logs for failing tool
2. Review findings in Security tab
3. Fix vulnerability or suppress false positive
4. Push fix and re-run

## Workflow Maintenance

### Updating Tool Versions

Tools auto-update via actions (e.g., `@master`, `@v3`).

For pinned versions, update manually:
```yaml
- uses: aquasecurity/trivy-action@0.15.0  # Update version here
```

### Adding New Tools

1. Add job to `security.yml`
2. Update `security-gate` dependencies
3. Document in `SECURITY_SCANNING.md`
4. Test with manual trigger

### Performance Optimization

**Caching**:
- Docker layers cached via `cache-from/cache-to`
- Python dependencies cached automatically

**Parallelization**:
- Jobs run concurrently where possible
- Use `needs:` for dependencies only

**Conditional Execution**:
```yaml
if: github.event_name == 'schedule'  # Run only on schedule
```

## Troubleshooting

### Rate Limiting

GitHub Actions has rate limits. If hit:
- Add caching
- Use conditional triggers
- Spread out scheduled runs

### Tool Authentication

Some tools require API keys:
- Snyk: Free tier available
- GitGuardian: Optional enhancement
- GitHub: Uses automatic `GITHUB_TOKEN`

### Scan Timeouts

If scans timeout:
- Increase timeout in workflow
- Optimize scan scope
- Split into separate workflows

## Best Practices

1. **Don't ignore failures** - Investigate all security alerts
2. **Review weekly reports** - Check scheduled run artifacts
3. **Keep tools updated** - Enable Dependabot for workflows
4. **Document suppressions** - Explain why alerts are dismissed
5. **Test locally first** - Run scans before pushing

## Support

- **Documentation**: [SECURITY_SCANNING.md](../../SECURITY_SCANNING.md)
- **Issues**: Open GitHub issue with `security` label
- **Questions**: Ask in PR comments or discussions

---

**Maintained by**: Security Team
**Last Updated**: 2026-01-10
