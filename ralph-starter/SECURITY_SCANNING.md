# Security Scanning - SEC-023

## Overview

Ralph Mode Bot implements comprehensive automated security scanning across the entire development lifecycle. This document describes the security scanning pipeline, tools used, and how to interpret results.

## Scanning Tools

### SAST (Static Application Security Testing)

#### 1. Semgrep
- **Purpose**: Fast, customizable static analysis
- **Runs on**: Every PR and push
- **Rulesets**:
  - `p/security-audit` - General security issues
  - `p/secrets` - Hardcoded secrets detection
  - `p/owasp-top-ten` - OWASP vulnerabilities
  - `p/python` - Python-specific issues
- **Threshold**: Fails on HIGH/CRITICAL findings
- **Reports**: SARIF uploaded to GitHub Security

#### 2. CodeQL
- **Purpose**: Deep semantic code analysis
- **Runs on**: Every PR and push
- **Queries**: `security-extended`, `security-and-quality`
- **Languages**: Python
- **Threshold**: Fails on security issues
- **Reports**: Integrated with GitHub Advanced Security

#### 3. Bandit
- **Purpose**: Python-specific security linter
- **Runs on**: Every PR and push
- **Configuration**: `.bandit` and `pyproject.toml`
- **Coverage**: 50+ Python security checks
- **Reports**: JSON artifact uploaded

### SCA (Software Composition Analysis)

#### 4. Snyk
- **Purpose**: Dependency vulnerability scanning
- **Runs on**: Every PR and push
- **Checks**: Known CVEs in dependencies
- **Threshold**: Fails on HIGH severity
- **Reports**: SARIF uploaded to GitHub Security
- **Note**: Requires `SNYK_TOKEN` secret

#### 5. Dependabot
- **Purpose**: Automated dependency updates
- **Runs on**: Pull requests only
- **Features**:
  - Vulnerability detection
  - License compliance checking
  - Automatic PR creation for updates

#### 6. Safety
- **Purpose**: Python package vulnerability scanner
- **Runs on**: Every PR and push
- **Database**: Safety DB (Python vulnerabilities)
- **Reports**: JSON artifact uploaded

### Secrets Scanning

#### 7. GitLeaks
- **Purpose**: Detect hardcoded secrets
- **Runs on**: Every commit
- **Coverage**:
  - API keys
  - Passwords
  - Tokens
  - Private keys
  - Database credentials
- **Threshold**: Fails immediately on detection

#### 8. TruffleHog
- **Purpose**: Secrets scanning with entropy detection
- **Runs on**: Every PR and push
- **Features**:
  - Entropy-based detection
  - Regex patterns
  - Verified secrets only (reduces false positives)
- **Threshold**: Fails on verified secrets

### Container Security

#### 9. Trivy
- **Purpose**: Container image vulnerability scanner
- **Runs on**: Every PR/push when Dockerfile changes
- **Scans**:
  - OS vulnerabilities
  - Application dependencies
  - Misconfigurations
- **Severity**: Reports CRITICAL, HIGH, MEDIUM
- **Threshold**: Fails on CRITICAL only

#### 10. Grype
- **Purpose**: Alternative container vulnerability scanner
- **Runs on**: Every PR/push when Dockerfile changes
- **Features**:
  - Multiple vulnerability databases
  - SBOM generation
  - High accuracy
- **Threshold**: Fails on HIGH severity

### DAST (Dynamic Application Security Testing)

#### 11. OWASP ZAP
- **Purpose**: Runtime security testing
- **Runs on**: Push to main only (staging deploys)
- **Configuration**: `.zap/rules.tsv`
- **Tests**:
  - XSS vulnerabilities
  - SQL Injection
  - CSRF issues
  - Security headers
  - Authentication flaws
- **Mode**: Baseline scan (passive)

### Additional Checks

#### 12. License Compliance
- **Tool**: pip-licenses
- **Runs on**: Every PR and push
- **Output**: JSON + Markdown reports
- **Purpose**: Track dependency licenses

## Workflow Triggers

### On Pull Request
- SAST (Semgrep, CodeQL, Bandit)
- SCA (Snyk, Dependabot, Safety)
- Secrets (GitLeaks, TruffleHog)
- Container (if Dockerfile changed)
- License compliance

### On Push to Main/Develop
- All PR checks PLUS:
- DAST (OWASP ZAP)
- Full container scan

### Weekly Schedule (Sunday 2 AM UTC)
- Complete security audit
- All scanning tools
- Comprehensive report generation
- GitHub issue creation if findings exist

### Manual Trigger
- Available via GitHub Actions UI
- Runs full scan suite

## Critical Findings - Build Failure Criteria

The pipeline will **FAIL** the build on:

1. **CRITICAL** container vulnerabilities (Trivy)
2. **HIGH** severity dependency vulnerabilities (Snyk, Safety)
3. **Any** secrets detected (GitLeaks, TruffleHog)
4. **Security issues** in code (Semgrep, CodeQL)
5. **HIGH** severity Python security issues (Bandit)
6. **CRITICAL/HIGH** OWASP ZAP findings (main branch only)

## Viewing Results

### GitHub Security Tab
1. Navigate to repository → Security tab
2. Click "Code scanning alerts"
3. Filter by:
   - Tool (Semgrep, CodeQL, Trivy, etc.)
   - Severity (Critical, High, Medium, Low)
   - Status (Open, Dismissed, Fixed)

### Workflow Artifacts
Download reports from Actions:
- `bandit-report.json` - Python security issues
- `safety-report.json` - Dependency vulnerabilities
- `license-report` - License compliance
- `weekly-security-report.md` - Comprehensive weekly report

### SARIF Files
All major tools output SARIF format for GitHub integration:
- Semgrep → `semgrep.sarif`
- CodeQL → Automatic integration
- Snyk → `snyk.sarif`
- Trivy → `trivy-results.sarif`
- Grype → Automatic SARIF

## Weekly Security Report

Every Sunday at 2 AM UTC, a comprehensive report is generated:

1. **Aggregates** all scan results
2. **Creates** a detailed markdown report
3. **Uploads** report as artifact
4. **Opens GitHub issue** if critical findings exist

### Report Contents
- Scan status summary table
- Action items prioritized by severity
- Recommendations for remediation
- Links to detailed findings

## Configuration Files

### `.zap/rules.tsv`
OWASP ZAP scanning rules and thresholds

### `.bandit`
Bandit configuration (deprecated, use pyproject.toml)

### `pyproject.toml`
- Bandit settings
- Code formatting (Black, isort)

### `.github/workflows/security.yml`
Complete security scanning pipeline

## Required GitHub Secrets

For full functionality, configure these secrets:

### Required
- `SNYK_TOKEN` - Snyk API token (free tier available)

### Optional
- `GITGUARDIAN_API_KEY` - GitGuardian secret scanning

## Best Practices

### For Developers

1. **Run scans locally** before pushing:
   ```bash
   # Python security
   bandit -r . -f screen

   # Dependency check
   safety check --file requirements.txt

   # Secrets scan
   gitleaks detect --source . --verbose
   ```

2. **Review security alerts** in PR checks
3. **Don't dismiss** alerts without understanding them
4. **Update dependencies** regularly
5. **Never commit secrets** - use environment variables

### For Security Team

1. **Monitor** weekly security reports
2. **Triage** findings by severity
3. **Track** remediation progress
4. **Update** scanning rules quarterly
5. **Review** dismissed alerts monthly

## Troubleshooting

### False Positives

If a tool reports a false positive:

1. **Verify** it's actually false (ask security team)
2. **Document** why it's safe in code comments
3. **Suppress** using tool-specific mechanisms:
   - Semgrep: `# nosemgrep: rule-id`
   - Bandit: `# nosec` or `# noqa: B###`
   - CodeQL: `.github/codeql/codeql-config.yml`

### Build Failures

If security gate fails:

1. **Check** which tool failed in Actions logs
2. **View** detailed findings in Security tab
3. **Assess** if it's a true positive
4. **Fix** the vulnerability or suppress if false positive
5. **Re-run** the checks

### Performance Issues

If scans are too slow:

1. **Enable caching** (already configured for Docker)
2. **Limit scope** for large repos
3. **Run heavy scans** on schedule only
4. **Parallelize** independent jobs

## Compliance

This scanning pipeline helps meet:

- **OWASP Top 10** - All SAST/DAST tools
- **PCI-DSS** - Container security, secrets scanning
- **GDPR** - Data exposure prevention
- **SOC 2** - Security monitoring, audit logs
- **Supply Chain Security** - SCA, SBOM generation

## Continuous Improvement

Security scanning is continuously improved:

- **Tools updated** automatically via Dependabot
- **Rulesets reviewed** quarterly
- **New tools added** as needed
- **Thresholds adjusted** based on team capacity

## Support

For security scanning questions:

- **Documentation**: This file
- **Tool Issues**: See vendor documentation
- **Security Concerns**: Contact security team
- **False Positives**: Open discussion in PR

---

**Last Updated**: 2026-01-10
**Owner**: Security Team
**Review Cycle**: Quarterly
