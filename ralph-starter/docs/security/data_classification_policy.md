# Ralph Mode - Data Classification Policy

**Version:** 1.0
**Effective Date:** January 2026
**Document Owner:** Security Team
**Review Cycle:** Annual

## 1. Purpose

This Data Classification Policy establishes a framework for categorizing data based on sensitivity, criticality, and regulatory requirements. It defines handling requirements, access controls, and protection measures for each classification level.

## 2. Scope

This policy applies to:
- All data created, processed, stored, or transmitted by Ralph Mode
- All employees, contractors, and service providers handling data
- All systems, applications, and storage media containing data
- Data throughout its entire lifecycle (creation to destruction)

## 3. Data Classification Levels

Ralph Mode uses a four-tier data classification system:

### 3.1 RESTRICTED
**Definition:** Highly sensitive data requiring maximum protection. Unauthorized disclosure could cause severe harm to the organization or individuals.

**Examples:**
- Production API keys and secrets (Telegram bot token, Groq API key)
- Database credentials and connection strings
- Encryption keys and certificates
- User authentication tokens
- Private SSH keys
- Payment processing credentials (if implemented)

**Handling Requirements:**
- Store in environment variables (`.env` files, never committed)
- Encrypt at rest (AES-256) and in transit (TLS 1.3)
- Access limited to authorized personnel only (named individuals)
- Rotate every 90 days minimum
- Audit all access attempts
- Never log, display, or transmit in plaintext
- Secure deletion required (overwrite, not just delete)

**Access Control:**
- Role-based access control (RBAC)
- Multi-factor authentication (MFA) required
- Just-in-time access provisioning
- Quarterly access reviews
- Immediate revocation upon termination

**Storage Locations:**
- Production: Secure secrets management system
- Development: Local `.env` files (in `.gitignore`)
- Never in: Version control, logs, screenshots, documentation

---

### 3.2 CONFIDENTIAL
**Definition:** Sensitive data requiring strong protection. Unauthorized disclosure could cause significant harm or competitive disadvantage.

**Examples:**
- User Personally Identifiable Information (PII):
  - Telegram user IDs
  - Username and display names
  - Chat message content
  - Location data (if collected)
- Business information:
  - Product roadmap and strategy
  - Financial projections
  - Partnership agreements
  - Customer lists
- Technical information:
  - Source code (proprietary components)
  - System architecture details
  - Security configurations
  - Penetration test results

**Handling Requirements:**
- Encrypt in transit (TLS 1.2+)
- Encrypt at rest for PII (AES-256)
- Access limited to role-based need
- Retain according to retention schedule
- Sanitize before sharing externally
- Log access for audit purposes

**Access Control:**
- Role-based access (minimum 2 roles: Admin, Developer)
- MFA recommended but not required
- Annual access reviews
- Approval required for external sharing

**Storage Locations:**
- Production database (encrypted)
- Secure file storage with access controls
- Encrypted backups
- Development environments (anonymized data preferred)

**Data Retention:**
- Active users: Duration of service use + 30 days
- Inactive users: 90 days after last activity, then purge
- Business data: 7 years (or per legal requirements)
- Logs: 90 days, then archive or delete

---

### 3.3 INTERNAL
**Definition:** Data intended for internal use only. Unauthorized disclosure could cause minor harm or inconvenience.

**Examples:**
- Internal documentation and wikis
- Development roadmap (non-strategic)
- System logs (sanitized)
- Team communication (non-confidential)
- Employee directory
- General business processes
- Non-sensitive analytics and metrics

**Handling Requirements:**
- Encrypted in transit (HTTPS)
- Access limited to employees and contractors
- No encryption at rest required (unless containing PII)
- Standard backup procedures
- Normal deletion procedures

**Access Control:**
- All authenticated employees/contractors
- No MFA required for read access
- Guest access prohibited

**Storage Locations:**
- Internal documentation platforms
- Shared drives with access controls
- Internal communication tools (Slack, email)
- Development repositories (private)

**Sharing:**
- Internal sharing allowed
- External sharing requires approval
- Can be shared with contractors under NDA

---

### 3.4 PUBLIC
**Definition:** Data approved for public disclosure. No harm from unauthorized access.

**Examples:**
- Marketing materials and website content
- Public documentation and guides
- Open source code (MIT license components)
- Press releases and blog posts
- Public API documentation
- Social media content
- `.env.example` template files
- Public GitHub repository contents

**Handling Requirements:**
- No special handling required
- Standard version control
- Attribution required (for open source)
- Consider reputation impact before publishing

**Access Control:**
- No access restrictions
- Anyone can view, copy, or share
- Modifications controlled via version control

**Storage Locations:**
- Public website (ralphmode.com)
- Public GitHub repositories
- Social media platforms
- Marketing platforms

**Publication Approval:**
- Marketing content: Marketing team approval
- Technical docs: Technical lead approval
- Code: Code review + license check
- All public content: Final review before publication

---

## 4. Data Classification Process

### 4.1 Classification Responsibility
- **Data Owner:** Responsible for classifying data (typically: team lead, product owner)
- **Data Custodian:** Implements and maintains controls (typically: DevOps, SysAdmin)
- **Data User:** Follows classification requirements (all personnel)

### 4.2 Classification Guidelines

**Decision Tree:**

```
Is it a secret/credential?
├─ Yes → RESTRICTED
└─ No ↓

Does it contain PII or could disclosure cause significant harm?
├─ Yes → CONFIDENTIAL
└─ No ↓

Is it approved for public disclosure?
├─ Yes → PUBLIC
└─ No → INTERNAL
```

### 4.3 When to Classify
Data must be classified:
- Upon creation or collection
- Before storage or transmission
- When sharing with third parties
- When regulatory requirements change
- During periodic reviews (annually)

### 4.4 Labeling Requirements

**File Naming:**
- Restricted: `[R]_filename` or folder: `/restricted/`
- Confidential: `[C]_filename` or folder: `/confidential/`
- Internal: `[I]_filename` or folder: `/internal/`
- Public: No label required

**Document Headers:**
```
Classification: [RESTRICTED | CONFIDENTIAL | INTERNAL | PUBLIC]
Owner: [Team/Individual]
Created: [Date]
Review Date: [Date]
```

**Code Comments:**
```python
# Classification: RESTRICTED
# DO NOT LOG OR DISPLAY
SECRET_KEY = os.getenv('SECRET_KEY')
```

---

## 5. Special Data Types

### 5.1 Personally Identifiable Information (PII)

**Definition:** Any information that can identify an individual person.

**Examples in Ralph Mode:**
- Telegram user ID (considered PII)
- Display name and username
- Profile pictures
- Message content
- Device information
- IP addresses

**Classification:** CONFIDENTIAL (minimum)

**Special Requirements:**
- GDPR and CCPA compliance
- User consent required for collection
- Right to access, rectify, and delete
- Data minimization (collect only what's needed)
- Purpose limitation (use only for stated purpose)
- Retention limits (delete when no longer needed)

**Handling:**
- Encrypt in transit and at rest
- Anonymize for analytics when possible
- Pseudonymize for development/testing
- Log access for audit
- Allow user data export (GDPR right to portability)
- Implement data deletion on request

### 5.2 Authentication Secrets

**Classification:** RESTRICTED

**Types:**
- API keys (Telegram, Groq, OpenWeather)
- OAuth tokens
- Session tokens
- Encryption keys
- Database passwords

**Handling:**
- Store in `.env` (local) or secrets manager (production)
- Never commit to Git
- Rotate every 90 days
- Revoke immediately if compromised
- Use environment-specific keys (dev/staging/prod)
- Implement key rotation without downtime

### 5.3 User-Generated Content

**Classification:** Varies based on content

**Examples:**
- Code snippets shared with bot → CONFIDENTIAL
- Project descriptions → INTERNAL or CONFIDENTIAL
- Feedback and bug reports → INTERNAL

**Handling:**
- Default to CONFIDENTIAL until reviewed
- Filter for sensitive data (secrets, PII)
- Sanitize before logging or sharing
- Respect user privacy settings
- Allow deletion on request

### 5.4 Logs and Monitoring Data

**Classification:** INTERNAL (if sanitized), CONFIDENTIAL (if containing PII)

**Requirements:**
- Sanitize PII before logging
- Never log passwords, API keys, or tokens
- Redact sensitive fields (e.g., `user_id=<REDACTED>`)
- Retain for 90 days, then delete
- Access limited to operations and security teams

**Example Sanitization:**
```python
# BAD - logs secret
logger.info(f"API call with key: {api_key}")

# GOOD - sanitized
logger.info(f"API call with key: {api_key[:8]}...")
```

---

## 6. Data Handling Requirements by Classification

### 6.1 Encryption

| Classification | In Transit | At Rest |
|---------------|-----------|---------|
| RESTRICTED | TLS 1.3 | AES-256 required |
| CONFIDENTIAL | TLS 1.2+ | AES-256 for PII |
| INTERNAL | HTTPS | Optional |
| PUBLIC | HTTPS | Not required |

### 6.2 Access Control

| Classification | Authentication | Authorization | MFA Required |
|---------------|---------------|---------------|--------------|
| RESTRICTED | Strong | Named individuals | Yes |
| CONFIDENTIAL | Standard | Role-based | Recommended |
| INTERNAL | Standard | All employees | No |
| PUBLIC | None | Public | No |

### 6.3 Backup and Recovery

| Classification | Backup | Encryption | Retention | Testing |
|---------------|--------|------------|-----------|---------|
| RESTRICTED | Daily | Yes | 30 days | Monthly |
| CONFIDENTIAL | Daily | Yes | 90 days | Quarterly |
| INTERNAL | Weekly | No | 30 days | Quarterly |
| PUBLIC | As needed | No | As needed | As needed |

### 6.4 Transmission

| Classification | Method | Approval Required | Sanitization |
|---------------|--------|-------------------|--------------|
| RESTRICTED | Encrypted channel | Executive | N/A |
| CONFIDENTIAL | Encrypted channel | Manager | Remove secrets |
| INTERNAL | Secure method | None | None |
| PUBLIC | Any method | Content review | None |

### 6.5 Disposal

| Classification | Method | Verification | Documentation |
|---------------|--------|--------------|---------------|
| RESTRICTED | Secure wipe (7-pass) | Certificate | Required |
| CONFIDENTIAL | Secure wipe (3-pass) | Audit log | Required |
| INTERNAL | Standard deletion | None | Optional |
| PUBLIC | Standard deletion | None | None |

---

## 7. Data Lifecycle Management

### 7.1 Creation
- Classify immediately upon creation
- Apply appropriate labels and metadata
- Set owner and review date
- Configure access controls

### 7.2 Storage
- Store according to classification requirements
- Encrypt sensitive data
- Implement access controls
- Regular backups per schedule

### 7.3 Use
- Access according to business need
- Log access to sensitive data
- Prevent unauthorized copying
- Monitor for anomalous access

### 7.4 Sharing
- Verify recipient authorization
- Use secure transmission methods
- Obtain approval as required
- Track external sharing

### 7.5 Archival
- Move inactive data to archive
- Maintain access controls
- Reduce access over time
- Document retention reason

### 7.6 Destruction
- Destroy per retention schedule
- Use appropriate disposal method
- Verify destruction
- Document disposal

---

## 8. Data Retention Schedule

| Data Type | Classification | Retention Period | Destruction Method |
|-----------|---------------|------------------|-------------------|
| User account data | CONFIDENTIAL | Duration + 30 days | Secure wipe |
| Chat logs | CONFIDENTIAL | 90 days | Secure deletion |
| Audit logs | INTERNAL | 90 days | Standard deletion |
| Backup data | Varies | 30-90 days | Secure wipe |
| API keys (rotated) | RESTRICTED | 0 days | Immediate revocation |
| Source code | PUBLIC/INTERNAL | Indefinite | N/A |
| Business records | CONFIDENTIAL | 7 years | Secure wipe |

---

## 9. Third-Party Data Sharing

### 9.1 Approved Third Parties

| Service | Data Shared | Classification | Purpose |
|---------|-------------|----------------|---------|
| Telegram | User messages | CONFIDENTIAL | Bot communication |
| Groq | Message content | CONFIDENTIAL | AI processing |
| Linode | All hosted data | Varies | Infrastructure |
| GitHub | Source code | PUBLIC/INTERNAL | Version control |

### 9.2 Data Processing Agreements
- Required for CONFIDENTIAL data or higher
- Must include security requirements
- Must specify data handling procedures
- Must allow audits
- Must comply with GDPR/CCPA

### 9.3 Data Transfer
- Assess recipient's security posture
- Obtain Data Processing Agreement (DPA)
- Use encrypted transmission
- Track all transfers
- Verify deletion when no longer needed

---

## 10. Compliance and Regulatory Requirements

### 10.1 GDPR (General Data Protection Regulation)
- Applies to EU residents' data
- PII classified as CONFIDENTIAL minimum
- User rights: access, rectification, deletion, portability
- Lawful basis for processing required
- Data Protection Impact Assessment (DPIA) for high-risk processing

### 10.2 CCPA (California Consumer Privacy Act)
- Applies to California residents
- Disclosure of data collection practices
- Right to opt-out of data sale (not applicable to Ralph Mode)
- Right to deletion

### 10.3 Industry Standards
- PCI-DSS (if payment processing added)
- HIPAA (not applicable unless health data processed)
- SOC 2 Type II (goal for future compliance)

---

## 11. Training and Awareness

### 11.1 Required Training
- All personnel: Data classification overview (annual)
- Developers: Secure coding and secrets management
- Operations: Data handling and disposal procedures
- Managers: Classification responsibilities

### 11.2 Training Content
- Classification levels and criteria
- Handling requirements for each level
- Real-world examples (Ralph Mode specific)
- Consequences of misclassification
- Incident reporting procedures

---

## 12. Monitoring and Enforcement

### 12.1 Compliance Monitoring
- Quarterly data classification audits
- Automated scanning for secrets in code
- Access log reviews
- User data handling spot checks

### 12.2 Violations and Consequences
- Incorrect classification: Re-training required
- Mishandling CONFIDENTIAL: Written warning
- Exposing RESTRICTED: Suspension or termination
- Intentional disclosure: Termination + legal action

---

## 13. Policy Review and Updates

### 13.1 Review Schedule
- Annual review by Security Team
- After security incidents involving data
- When regulations change
- When new data types are introduced

### 13.2 Reclassification
Data may be reclassified when:
- Sensitivity changes
- Regulatory requirements change
- Business needs evolve
- Data becomes public
- Retention period expires

---

## 14. Related Policies

- Information Security Policy
- Acceptable Use Policy
- Access Control Policy
- Incident Response Plan
- Privacy Policy
- Data Retention Policy

---

## 15. Approval

This policy has been reviewed and approved by:

- **Chief Technology Officer**
- **Security Lead**
- **Data Protection Officer**
- **Legal Counsel**

---

**For questions or clarification, contact:** security@ralphmode.com

**Version History:**
- v1.0 (January 2026): Initial release
