# Vendor Risk Assessment Framework

**Version**: 1.0
**Effective Date**: 2026-01-10
**Review Frequency**: Annually
**Owner**: Security Team

## 1. Purpose

This framework establishes a standardized process for assessing and managing third-party vendor risks to ensure:
- Vendor security controls meet our standards
- Data shared with vendors is protected
- Vendor incidents don't compromise our security
- Compliance with SOC 2 and GDPR requirements

## 2. Scope

This framework applies to all third-party vendors who:
- Process, store, or transmit Ralph Mode data
- Have access to Ralph Mode systems
- Provide critical services affecting availability
- Handle personally identifiable information (PII)

## 3. Vendor Classification

### 3.1 Risk Tiers

**High Risk**:
- Infrastructure providers (hosting, cloud services)
- Payment processors
- Vendors with access to production systems
- Vendors processing PII or sensitive data
- Single point of failure vendors

**Medium Risk**:
- API providers with limited data access
- Development tools with code access
- Analytics platforms
- Communication platforms

**Low Risk**:
- Marketing tools (no PII)
- Public data services
- Content delivery networks
- Minor SaaS tools

### 3.2 Data Classification

What data does the vendor access?

- **Public**: No restrictions (e.g., marketing content)
- **Internal**: Business information, not for public (e.g., roadmaps)
- **Confidential**: Sensitive business data (e.g., financial records)
- **Restricted**: Highly sensitive (e.g., PII, credentials, encryption keys)

## 4. Assessment Process

### 4.1 Initial Assessment (Before Engagement)

**Step 1: Business Justification**
- What problem does this vendor solve?
- Are there alternatives?
- What's the business impact if vendor fails?

**Step 2: Data Flow Mapping**
- What data will be shared?
- How is data transmitted?
- Where is data stored?
- How long is data retained?
- Who has access to the data?

**Step 3: Vendor Security Review**

**For High-Risk Vendors**:
- [ ] SOC 2 Type II report (within last 12 months)
- [ ] Security questionnaire completed
- [ ] Privacy policy reviewed
- [ ] Data processing addendum (DPA) signed
- [ ] Incident notification agreement
- [ ] Right to audit clause in contract
- [ ] Business continuity plan reviewed

**For Medium-Risk Vendors**:
- [ ] Security questionnaire completed
- [ ] Privacy policy reviewed
- [ ] DPA signed (if processing PII)
- [ ] Incident notification agreement

**For Low-Risk Vendors**:
- [ ] Privacy policy reviewed
- [ ] Terms of service reviewed
- [ ] No PII sharing confirmed

**Step 4: Contract Review**
- Data ownership clauses
- Liability and indemnification
- Service level agreements (SLAs)
- Termination and data return procedures
- Security breach notification requirements
- Audit rights
- Data deletion upon termination

**Step 5: Risk Decision**
- Document risks identified
- Define mitigation strategies
- Approve or reject vendor engagement
- Set reassessment date

### 4.2 Ongoing Monitoring

**Annual Reassessment**:
- Review SOC 2 report (if applicable)
- Verify no security incidents
- Confirm SLA compliance
- Update security questionnaire
- Review contract for renewals

**Continuous Monitoring**:
- Track vendor security incidents (public disclosures)
- Monitor vendor uptime/performance
- Review vendor security updates
- Track support responsiveness

**Quarterly Review**:
- Vendor inventory up to date
- High-risk vendors on schedule for reassessment
- No new security concerns

### 4.3 Vendor Offboarding

When terminating vendor relationship:
1. Notify vendor of termination
2. Request data deletion confirmation
3. Revoke all access credentials
4. Remove integrations
5. Verify data deletion (certificate of destruction)
6. Archive vendor assessment documentation

## 5. Vendor Inventory

### 5.1 Current Vendors

**Updated**: 2026-01-10

#### High-Risk Vendors

**1. Linode (Infrastructure Hosting)**
- **Service**: Virtual private servers, hosting
- **Data Classification**: Restricted (entire application + database)
- **Risk Level**: High (single point of failure)
- **SOC 2**: Available upon request from Linode
- **Assessment Date**: 2026-01-10
- **Next Review**: 2026-07-10 (6 months for critical vendor)
- **Contract End**: N/A (month-to-month)
- **SLA**: 99.9% uptime
- **Mitigations**:
  - Daily automated backups
  - Multi-region failover plan (documented)
  - Infrastructure as Code (Terraform) for rapid rebuild
  - Disaster recovery plan tested quarterly

#### Medium-Risk Vendors

**2. Groq (AI API)**
- **Service**: LLM API for agent responses
- **Data Classification**: Internal (user messages, context)
- **Risk Level**: Medium
- **SOC 2**: N/A (check if available)
- **Assessment Date**: 2026-01-10
- **Next Review**: 2027-01-10
- **Contract End**: N/A (pay-as-you-go)
- **SLA**: Best effort
- **Mitigations**:
  - API fallback to other providers (Anthropic, OpenAI)
  - Rate limiting to prevent abuse
  - Data retention: 30 days per Groq policy
  - No PII sent to Groq (sanitization layer)

**3. Telegram (Bot Platform)**
- **Service**: Messaging platform for bot
- **Data Classification**: Confidential (user messages, bot commands)
- **Risk Level**: Medium
- **SOC 2**: N/A (platform provider)
- **Assessment Date**: 2026-01-10
- **Next Review**: 2027-01-10
- **Contract End**: N/A (free platform)
- **SLA**: Best effort
- **Mitigations**:
  - End-to-end encryption for bot messages
  - Minimal data stored (transient processing)
  - Bot token rotation capability
  - Alternative messaging platforms identified (Discord, Slack)

**4. GitHub (Code Repository & CI/CD)**
- **Service**: Source code hosting, version control
- **Data Classification**: Confidential (proprietary code)
- **Risk Level**: Medium
- **SOC 2**: Available (GitHub Enterprise)
- **Assessment Date**: 2026-01-10
- **Next Review**: 2027-01-10
- **Contract End**: N/A (public repo, upgrade to Team if needed)
- **SLA**: 99.9% for Enterprise
- **Mitigations**:
  - Branch protection rules enforced
  - 2FA required for all contributors
  - Secrets scanning enabled
  - Daily backups via GitHub Actions
  - Alternative: GitLab (self-hosted option)

#### Low-Risk Vendors

**5. Tenor (GIF API)**
- **Service**: GIF search and delivery for bot entertainment
- **Data Classification**: Public (no sensitive data shared)
- **Risk Level**: Low
- **SOC 2**: N/A
- **Assessment Date**: 2026-01-10
- **Next Review**: 2027-01-10
- **Contract End**: N/A (free API)
- **SLA**: Best effort
- **Mitigations**:
  - Graceful degradation (bot works without GIFs)
  - Alternative: Giphy API (easy swap)
  - Rate limiting to prevent abuse

## 6. Security Questionnaire Template

### 6.1 For High/Medium Risk Vendors

**Company Information**
- Company name and headquarters location
- Years in business
- Number of employees
- Primary data center locations
- SOC 2 / ISO 27001 certification status

**Data Security**
- Encryption at rest (algorithm, key management)
- Encryption in transit (TLS version)
- Data backup frequency and retention
- Data center physical security
- Geographic data residency options

**Access Control**
- Multi-factor authentication (MFA) available?
- Role-based access control (RBAC)?
- Access logging and monitoring?
- Password policies
- Session timeout settings

**Incident Response**
- Incident response plan in place?
- Breach notification timeline (contractual commitment)
- Contact information for security incidents
- Recent security incidents (past 24 months)
- Public security advisories

**Compliance**
- GDPR compliance status
- CCPA compliance status
- PCI DSS (if applicable)
- HIPAA (if applicable)
- Data processing addendum available?

**Business Continuity**
- Disaster recovery plan tested?
- RTO/RPO commitments
- Redundancy and failover capability
- Business continuity plan

**Vendor Management**
- Subcontractors used?
- Subcontractor security requirements
- Right to audit subcontractors?

## 7. Risk Mitigation Strategies

### 7.1 Common Mitigations

**For Vendors Without SOC 2**:
- Enhanced contractual protections
- More frequent reassessments (quarterly)
- Limited data sharing
- Additional monitoring
- Alternative vendor identified

**For Single Points of Failure**:
- Disaster recovery plan
- Data backups (independent of vendor)
- Alternative vendor identified and documented
- Failover procedures tested

**For PII Processing Vendors**:
- Data processing addendum (DPA) required
- Encryption in transit and at rest
- Data minimization (only share what's needed)
- Data retention limits
- Breach notification SLA

**For Critical Availability Vendors**:
- SLA with financial penalties
- Multi-vendor strategy (no single point of failure)
- Monitoring and alerting
- Escalation procedures

## 8. Vendor Incident Response

### 8.1 When Vendor Has Security Breach

1. **Notification**: Vendor must notify us within 24 hours (per contract)
2. **Assessment**: Security team assesses impact to Ralph Mode
3. **Containment**: Isolate affected systems/data if needed
4. **Communication**: Notify affected users if PII compromised
5. **Remediation**: Work with vendor on remediation
6. **Review**: Reassess vendor risk rating
7. **Decision**: Continue, modify, or terminate relationship

### 8.2 When Vendor Has Availability Issue

1. **Detection**: Monitoring alerts or user reports
2. **Verification**: Confirm vendor issue (not our infrastructure)
3. **Workaround**: Activate failover or degraded mode
4. **Communication**: Status page update for users
5. **Escalation**: Contact vendor support
6. **Resolution**: Verify service restored
7. **Post-mortem**: Review with vendor, improve monitoring

## 9. Vendor Assessment Documentation

### 9.1 Assessment Record Template

**Vendor**: [Name]
**Assessment Date**: YYYY-MM-DD
**Assessor**: [Name, Title]
**Vendor Contact**: [Name, Email]

**Risk Rating**: High / Medium / Low

**Data Classification**: Public / Internal / Confidential / Restricted

**SOC 2 Report**:
- [ ] Reviewed (Date: YYYY-MM-DD, Type I / Type II)
- [ ] Not applicable
- [ ] Requested, pending

**Security Questionnaire**:
- [ ] Completed (attached)
- [ ] Not required (low risk)

**Findings**:
- [List any concerns or gaps]

**Mitigations**:
- [Actions taken to address risks]

**Decision**:
- [ ] Approved for engagement
- [ ] Approved with conditions: [specify]
- [ ] Rejected

**Next Review Date**: YYYY-MM-DD

**Approval**: [Name, Title, Date]

### 9.2 Storage Location

All vendor assessments stored in: `evidence/soc2/vendor_assessments/`

Retention: Life of vendor relationship + 7 years

Access: Security team, compliance team, auditors only

## 10. Roles & Responsibilities

**Security Team**:
- Conduct vendor security assessments
- Review SOC 2 reports
- Maintain vendor inventory
- Track reassessment dates
- Incident response coordination

**Procurement/Finance**:
- Contract review and negotiation
- Vendor relationship management
- SLA tracking

**Engineering**:
- Technical integration review
- Data flow mapping
- Implementation of security controls

**Legal**:
- Contract approval
- Data processing addendum review
- Liability and indemnification terms

## 11. Metrics

**Tracked Quarterly**:
- Total vendors by risk tier
- % of high-risk vendors with current SOC 2
- % of vendors with DPA signed
- Overdue reassessments
- Vendor security incidents
- SLA compliance

**Targets**:
- 100% of high-risk vendors with SOC 2 or compensating controls
- 100% of PII vendors with DPA
- 0 overdue reassessments
- <2 vendor security incidents per year

---

**Document History**:

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-10 | Ralph Agent | Initial vendor risk assessment framework |

**Approved By**: Security Team Lead
**Next Review Date**: 2027-01-10
