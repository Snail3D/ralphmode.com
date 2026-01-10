# Supply Chain Security (SEC-030)

This document describes the supply chain security measures implemented in Ralph Mode.

## Overview

Supply chain attacks target the software development and distribution process. We protect against these threats through multiple layers of security.

## Security Measures

### 1. Signed Commits

#### Why It Matters
Signed commits verify that code changes come from trusted developers, preventing attackers from impersonating contributors.

#### Setup for Developers

**Generate GPG Key:**
```bash
# Generate key
gpg --full-generate-key
# Choose RSA and RSA (default)
# Use 4096 bit key size
# Key doesn't expire (or set expiration)
# Enter your name and email (must match GitHub)

# List keys
gpg --list-secret-keys --keyid-format=long

# Note the key ID (after sec rsa4096/)
# Example: sec rsa4096/ABC123DEF456 -> Key ID is ABC123DEF456
```

**Configure Git:**
```bash
# Set your GPG key
git config --global user.signingkey ABC123DEF456

# Enable automatic signing
git config --global commit.gpgsign true
git config --global tag.gpgsign true

# Set GPG program (if needed)
git config --global gpg.program gpg
```

**Add to GitHub:**
```bash
# Export public key
gpg --armor --export ABC123DEF456

# Copy the output and add to GitHub:
# Settings → SSH and GPG keys → New GPG key
```

**Test It:**
```bash
# Create a signed commit
git commit -m "test: verify GPG signing"

# Verify it's signed
git log --show-signature -1

# Should see "Good signature from..."
```

#### Verification in CI

Our supply-chain.yml workflow automatically checks commit signatures. While not currently blocking (to ease onboarding), unsigned commits generate warnings.

**Future Plan:** Require signed commits on main branch via branch protection rules.

### 2. Package Integrity

#### Lockfile with Hashes

We use `requirements.lock` with SHA256 hashes to ensure package integrity.

**Updating Dependencies:**

```bash
# Install pip-tools
pip install pip-tools

# Update lockfile after changing requirements.txt
pip-compile --generate-hashes --output-file=requirements.lock requirements.txt

# Install with hash verification
pip install --require-hashes -r requirements.lock
```

**Why Hashes Matter:**
- Detects tampering with packages on PyPI
- Ensures reproducible builds
- Prevents malicious package replacements

#### Typosquat Detection

Our CI automatically checks for common typosquat packages (malicious packages with names similar to popular ones).

**Examples We Block:**
- `python-telegram` → Correct: `python-telegram-bot`
- `request` → Correct: `requests`
- `flask-cor` → Correct: `flask-cors`

### 3. Dependency Pinning

**Philosophy:**
- `requirements.txt`: Uses `>=` for flexibility during development
- `requirements.lock`: Exact versions with hashes for production

**Production Deployment:**
```bash
# Always use lockfile in production
pip install --require-hashes -r requirements.lock
```

### 4. Software Bill of Materials (SBOM)

SBOMs are automatically generated on each release.

**Formats:**
- **CycloneDX** (JSON/XML): Industry standard, machine-readable
- **SPDX**: Linux Foundation standard, licensing focus

**Access SBOMs:**
- Attached to GitHub releases
- Available as workflow artifacts
- Generated with: `workflow_dispatch` event

**Manual Generation:**
```bash
# Install tools
pip install cyclonedx-bom spdx-tools

# Generate CycloneDX
cyclonedx-py --format json --output sbom.json

# Generate SPDX (see workflow for full script)
```

### 5. Third-Party Code Review

**Policy:**
- Prefer pip packages over vendored code
- Document any vendored code in `third_party/README.md`
- Review licenses for compatibility
- Track security advisories for all dependencies

**Checking Dependencies:**
```bash
# List all dependencies
pip list

# Check for vulnerabilities
pip install safety
safety check --file requirements.lock

# Check licenses
pip install pip-licenses
pip-licenses --format=markdown
```

### 6. CI/CD Pipeline Security

**GitHub Actions Security:**

1. **Principle of Least Privilege**
   - Each workflow specifies minimum required permissions
   - No `permissions: write-all` allowed

2. **Action Pinning**
   - Currently pinned to major versions (e.g., `@v4`)
   - Future: Pin to commit SHAs for immutability

3. **Secrets Management**
   - Never hardcode secrets in workflows
   - Always use `${{ secrets.SECRET_NAME }}`
   - Secrets are encrypted at rest by GitHub

4. **Workflow Isolation**
   - Each job runs in fresh environment
   - Prevents contamination between runs

**Workflow File Checks:**
```bash
# Check for security issues
grep -r "permissions: write-all" .github/workflows/
grep -r "password\|secret" .github/workflows/ | grep -v "secrets\."
```

### 7. Build Reproducibility

Reproducible builds prove that binaries match source code.

**How We Ensure It:**
- Pinned dependencies with hashes
- Deterministic build process
- Sorted file archives with fixed timestamps
- CI verifies builds are byte-for-byte identical

**Local Verification:**
```bash
# Build twice
pip install -r requirements.lock
tar -czf build1.tar.gz --sort=name --mtime='1970-01-01' *.py requirements.txt requirements.lock

pip uninstall -r requirements.lock -y
pip install -r requirements.lock
tar -czf build2.tar.gz --sort=name --mtime='1970-01-01' *.py requirements.txt requirements.lock

# Compare
sha256sum build1.tar.gz build2.tar.gz
# Should be identical
```

## CI/CD Checks

The `supply-chain.yml` workflow runs on every PR and push:

- ✅ **verify-commits**: Check commit signatures (informational)
- ✅ **verify-packages**: Verify lockfile and hash integrity
- ✅ **verify-pinning**: Ensure lockfile exists
- ✅ **review-third-party**: Check for vendored code
- ✅ **verify-cicd-security**: Audit workflow permissions
- ✅ **verify-reproducibility**: Confirm builds are reproducible
- ✅ **generate-sbom**: Create SBOM on releases

**Blocking vs Non-Blocking:**
- **Blocking**: Package verification, pinning, CI/CD security, reproducibility
- **Informational**: Commit signatures (warnings only)

## Best Practices

### For Developers

1. **Sign your commits** (helps build trust)
2. **Update lockfile** after changing `requirements.txt`
3. **Review dependency updates** (don't blindly upgrade)
4. **Run security scans** before committing
5. **Use verified publishers** on PyPI when possible

### For Maintainers

1. **Enable branch protection** requiring signed commits (future)
2. **Review SBOMs** before releases
3. **Audit third-party code** additions
4. **Monitor security advisories** (GitHub Dependabot)
5. **Rotate secrets** periodically

### For Deployers

1. **Always use `requirements.lock`** in production
2. **Verify signatures** on releases
3. **Check SBOMs** against expected dependencies
4. **Monitor runtime** for unexpected behavior
5. **Keep systems patched**

## Security Incident Response

**If you discover a supply chain security issue:**

1. **Do NOT open a public issue**
2. Email security contact (see SECURITY.md)
3. Include:
   - Description of the issue
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if known)

## Further Reading

- [Secure Supply Chain Consumption Framework (S2C2F)](https://github.com/ossf/s2c2f)
- [SLSA (Supply-chain Levels for Software Artifacts)](https://slsa.dev/)
- [Sigstore](https://www.sigstore.dev/)
- [CycloneDX](https://cyclonedx.org/)
- [SPDX](https://spdx.dev/)
- [GitHub Code Security](https://docs.github.com/en/code-security)

## Compliance

This implementation addresses:

- **NIST SP 800-218**: Secure Software Development Framework (SSDF)
- **EO 14028**: Improving the Nation's Cybersecurity (SBOM requirement)
- **SLSA Level 2**: Build integrity and provenance
- **OpenSSF Scorecard**: Supply chain security metrics

---

**Status**: ✅ Implemented (SEC-030)
**Last Updated**: 2026-01-10
**Owner**: Security Team
