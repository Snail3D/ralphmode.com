# Ralph Mode - Business Continuity Plan (BCP)

**Version:** 1.0
**Effective Date:** January 2026
**Document Owner:** CTO / Operations Team
**Review Cycle:** Annual

## 1. Purpose

This Business Continuity Plan (BCP) ensures Ralph Mode can maintain or rapidly restore critical operations during and after disruptive events. It defines procedures, responsibilities, and resources needed to minimize downtime, protect data, and ensure service continuity for users.

## 2. Scope

This plan covers:
- Critical business functions and systems
- Disaster recovery procedures for infrastructure and data
- Emergency communication protocols
- Personnel roles and responsibilities
- Recovery time objectives (RTO) and recovery point objectives (RPO)

## 3. Business Impact Analysis

### 3.1 Critical Business Functions

| Function | Description | RTO | RPO | Priority |
|----------|-------------|-----|-----|----------|
| Telegram Bot Service | Core bot functionality for users | 4 hours | 1 hour | P0 (Critical) |
| User Data Storage | Database availability | 4 hours | 15 minutes | P0 (Critical) |
| AI Processing (Groq) | LLM API integration | 8 hours | N/A | P1 (High) |
| Authentication | User login and session management | 4 hours | 1 hour | P1 (High) |
| Monitoring & Logging | System observability | 24 hours | 4 hours | P2 (Medium) |
| Documentation/Website | Public documentation and landing page | 72 hours | 24 hours | P3 (Low) |

**Definitions:**
- **RTO (Recovery Time Objective):** Maximum acceptable downtime
- **RPO (Recovery Point Objective):** Maximum acceptable data loss (time)

### 3.2 Impact of Disruption

**Financial Impact:**
- User churn: Loss of active users due to extended downtime
- Revenue loss: Potential subscription revenue if monetized
- Recovery costs: Emergency support, infrastructure scaling, overtime

**Reputational Impact:**
- User trust erosion from extended outages
- Negative social media sentiment
- Media coverage of major incidents

**Operational Impact:**
- Development delays while handling incident
- Support ticket volume spike
- Team morale impact

---

## 4. Risk Assessment

### 4.1 Potential Disruption Scenarios

#### Infrastructure Failures

**Scenario 1: Linode Data Center Outage**
- **Likelihood:** Low (Linode has 99.9% uptime SLA)
- **Impact:** High (complete service disruption)
- **Mitigation:** Multi-region deployment, cloud provider diversification (future)
- **Recovery Strategy:** Failover to backup region or provider

**Scenario 2: Database Corruption/Failure**
- **Likelihood:** Medium (hardware failure, software bug)
- **Impact:** Critical (data loss, service unavailable)
- **Mitigation:** Automated backups (every 6 hours), replication
- **Recovery Strategy:** Restore from most recent backup

**Scenario 3: Network/DDoS Attack**
- **Likelihood:** Medium (public service attracts attacks)
- **Impact:** High (service degradation or unavailability)
- **Mitigation:** DDoS protection (Cloudflare, Linode), rate limiting
- **Recovery Strategy:** Enable upstream DDoS protection, scale infrastructure

---

#### Software Failures

**Scenario 4: Buggy Deployment**
- **Likelihood:** Medium (despite testing, bugs happen)
- **Impact:** Medium-High (service disruption, data corruption risk)
- **Mitigation:** Staging environment, automated testing, gradual rollout
- **Recovery Strategy:** Rollback to previous version

**Scenario 5: Third-Party API Outage (Groq, Telegram)**
- **Likelihood:** Medium (external dependencies)
- **Impact:** High (core functionality unavailable)
- **Mitigation:** Fallback LLM provider (OpenAI, Anthropic), error handling
- **Recovery Strategy:** Switch to backup provider, queue requests

**Scenario 6: Dependency Vulnerability (Supply Chain)**
- **Likelihood:** Medium (npm/pip packages)
- **Impact:** High (security vulnerability, service disruption)
- **Mitigation:** Dependency scanning, version pinning
- **Recovery Strategy:** Patch, update, or replace vulnerable dependency

---

#### Human Factors

**Scenario 7: Key Personnel Unavailable**
- **Likelihood:** Medium (illness, departure, emergency)
- **Impact:** Medium (delayed response to incidents)
- **Mitigation:** Documentation, cross-training, on-call rotation
- **Recovery Strategy:** Activate backup personnel, escalate to team

**Scenario 8: Accidental Data Deletion**
- **Likelihood:** Low (access controls limit risk)
- **Impact:** High (data loss)
- **Mitigation:** Backup retention, soft deletes, access controls
- **Recovery Strategy:** Restore from backup, audit logs

**Scenario 9: Insider Threat/Malicious Actor**
- **Likelihood:** Low (small team, trusted members)
- **Impact:** Critical (data breach, sabotage)
- **Mitigation:** Access controls, audit logging, separation of duties
- **Recovery Strategy:** Incident response, forensic investigation

---

#### External Events

**Scenario 10: Natural Disaster (Data Center Location)**
- **Likelihood:** Low (depends on geography)
- **Impact:** Critical (complete infrastructure loss)
- **Mitigation:** Geographic diversity, cloud-based infrastructure
- **Recovery Strategy:** Failover to alternate region

**Scenario 11: Internet Backbone Disruption**
- **Likelihood:** Very Low
- **Impact:** High (connectivity issues)
- **Mitigation:** Multiple network providers (if feasible)
- **Recovery Strategy:** Wait for restoration, communicate with users

**Scenario 12: Legal/Regulatory Action**
- **Likelihood:** Low (compliance-focused approach)
- **Impact:** High (service shutdown, data access restrictions)
- **Mitigation:** Legal compliance, terms of service, privacy policy
- **Recovery Strategy:** Legal counsel engagement, compliance remediation

---

## 5. Business Continuity Strategies

### 5.1 Infrastructure Redundancy

**Current State:**
- Single Linode server (69.164.201.191)
- Single database instance
- No failover or high availability

**Future State (Roadmap):**
- **Multi-region deployment:** Primary (US East) + Secondary (US West or EU)
- **Database replication:** Primary-secondary replication with auto-failover
- **Load balancing:** Distribute traffic across multiple instances
- **CDN:** Static assets on CDN (Cloudflare, AWS CloudFront)

**Implementation Priority:** High (next 6 months)

### 5.2 Data Protection and Backup

**Backup Strategy:**

**Database Backups:**
- **Frequency:** Every 6 hours (0:00, 6:00, 12:00, 18:00 UTC)
- **Retention:**
  - Last 7 days: All backups (4/day × 7 = 28 backups)
  - Last 30 days: Daily backups (1/day × 30 = 30 backups)
  - Last 12 months: Monthly backups (1/month × 12 = 12 backups)
- **Storage:** Encrypted (AES-256), off-server location (Linode Object Storage or AWS S3)
- **Testing:** Monthly restore test to verify backup integrity

**Code Repository:**
- **Platform:** GitHub (git-based version control)
- **Frequency:** Real-time (every commit pushed)
- **Retention:** Indefinite (git history preserved)
- **Protection:** Branch protection on main, required reviews

**Configuration and Secrets:**
- **Backup:** Weekly manual backup of `.env.example` and infrastructure configs
- **Storage:** Encrypted USB drive (physical) + encrypted cloud storage
- **Secrets:** NOT backed up to cloud; stored in password manager (1Password)

**Backup Verification:**
```bash
# Monthly backup restore test
1. Download most recent backup
2. Restore to test database instance
3. Verify data integrity (row counts, key records)
4. Test application connection to restored DB
5. Document results in ops log
```

### 5.3 Failover and Recovery Procedures

**Automatic Failover (Future Implementation):**
- Health checks every 60 seconds
- If primary fails 3 consecutive checks, failover triggered
- DNS updated to point to secondary (TTL: 60 seconds)
- Total failover time: <5 minutes

**Manual Failover (Current State):**
1. Detect outage (monitoring alert or user reports)
2. Verify primary server is down (SSH, ping, HTTP check)
3. Restore from backup to new Linode instance
4. Update DNS A record to new server IP
5. Test functionality
6. Communicate with users

**Expected Recovery Time (Manual):**
- Detection: 5-15 minutes
- Decision to failover: 5 minutes
- Spin up new server: 10 minutes
- Restore from backup: 30 minutes
- DNS propagation: 15 minutes (TTL)
- Testing: 10 minutes
- **Total: ~1.5 hours**

---

## 6. Emergency Response Procedures

### 6.1 Incident Detection

**Monitoring and Alerting:**
- **Uptime monitoring:** UptimeRobot or Pingdom (check every 5 minutes)
- **Error rate monitoring:** Application logs, error tracking (Sentry)
- **Performance monitoring:** Response times, resource usage
- **User reports:** Email, Telegram, social media

**Alert Escalation:**
1. Automated alert sent to on-call engineer (PagerDuty, email, SMS)
2. If no acknowledgment in 15 minutes, escalate to backup
3. If critical (P0), immediately alert CTO

### 6.2 Emergency Communication

**Internal Communication:**
- **Slack #incidents:** Real-time updates during outage
- **Email:** Status updates every 30 minutes for P0, hourly for P1
- **Video call:** For complex incidents requiring coordination

**External Communication:**

**Status Page (status.ralphmode.com):**
- Update within 15 minutes of confirmed outage
- Provide estimated recovery time (or "investigating")
- Update every 30 minutes with progress

**User Notification:**
- **Email:** For outages exceeding 2 hours
- **Social media (Twitter/X):** Real-time updates
- **In-app notification:** When service restores

**Communication Template:**
```
🚨 INCIDENT UPDATE - [Time UTC]

STATUS: [Investigating | Identified | Monitoring | Resolved]

We are currently experiencing [brief description of issue].
Our team is actively working to restore service.

IMPACT: [What's affected]
CAUSE: [If known]
ETA: [Estimated restoration time or "Under investigation"]

We apologize for the inconvenience and will provide updates every 30 minutes.

Next update: [Time UTC]
```

### 6.3 Emergency Contact List

**On-Call Rotation:**
| Week | Primary On-Call | Secondary On-Call | Escalation (CTO) |
|------|----------------|-------------------|------------------|
| Week 1 | [Name/Contact] | [Name/Contact] | [Name/Contact] |
| Week 2 | [Name/Contact] | [Name/Contact] | [Name/Contact] |
| Week 3 | [Name/Contact] | [Name/Contact] | [Name/Contact] |
| Week 4 | [Name/Contact] | [Name/Contact] | [Name/Contact] |

**External Contacts:**
| Service | Contact | Phone | URL |
|---------|---------|-------|-----|
| Linode Support | - | - | https://www.linode.com/support |
| GitHub Support | - | - | https://support.github.com |
| Groq Support | - | - | [Support email] |
| Domain Registrar (GoDaddy) | - | - | https://www.godaddy.com/contact-us |

---

## 7. Recovery Procedures by Scenario

### 7.1 Linode Server Failure

**Symptoms:**
- Server unreachable via SSH
- HTTP/HTTPS requests timeout
- Monitoring alerts trigger

**Recovery Steps:**

**Step 1: Verify Outage (5 minutes)**
```bash
# Test connectivity
ping 69.164.201.191
curl -I https://ralphmode.com

# Check Linode status page
# https://status.linode.com

# Attempt SSH
ssh root@69.164.201.191
```

**Step 2: Determine Root Cause (10 minutes)**
- Check Linode dashboard for server status
- Review console logs if accessible
- Determine if hardware failure, network issue, or software crash

**Step 3: Decide Recovery Approach**

**Option A: Reboot (if software crash)**
```bash
# Via Linode dashboard: Reboot server
# Wait 5 minutes for boot
# Test service restoration
```

**Option B: Restore from Backup (if hardware failure)**
1. Create new Linode instance (same size or larger)
2. Restore latest database backup
3. Clone git repository and deploy application
4. Update DNS A record to new IP
5. Test functionality
6. Monitor for stability

**Step 4: Update DNS (if new server)**
```bash
# Update GoDaddy DNS A record
@ -> [New IP Address]
www -> [New IP Address]

# TTL: 600 seconds (10 minutes)
```

**Step 5: Verify and Monitor (30 minutes)**
- Test all critical functions
- Monitor error rates and performance
- Verify backup job is running on new server

**Step 6: Post-Incident**
- Document root cause
- Update BCP if needed
- Conduct post-mortem

**Total Recovery Time:** 1-2 hours

---

### 7.2 Database Corruption or Data Loss

**Symptoms:**
- Application errors related to database queries
- Data inconsistencies reported by users
- Database integrity check failures

**Recovery Steps:**

**Step 1: Assess Damage (15 minutes)**
```bash
# Stop application to prevent further corruption
sudo systemctl stop ralph-bot

# Check database integrity
# (Example for PostgreSQL)
sudo -u postgres psql -c "VACUUM FULL ANALYZE;"

# Check for corruption
# (Example for PostgreSQL)
sudo -u postgres pg_dump dbname > /tmp/test_dump.sql
```

**Step 2: Determine Recovery Point**
- Identify last known good backup
- Estimate data loss window (time since last backup)
- Assess criticality of lost data

**Step 3: Restore from Backup**
```bash
# Create backup of current (corrupted) database
pg_dump ralphmode > /tmp/corrupted_backup_$(date +%Y%m%d_%H%M%S).sql

# Download latest backup from object storage
aws s3 cp s3://ralphmode-backups/latest.sql /tmp/restore.sql

# Drop existing database (CAUTION!)
sudo -u postgres psql -c "DROP DATABASE ralphmode;"

# Create new database
sudo -u postgres psql -c "CREATE DATABASE ralphmode;"

# Restore from backup
sudo -u postgres psql ralphmode < /tmp/restore.sql

# Verify data
sudo -u postgres psql -d ralphmode -c "SELECT COUNT(*) FROM users;"
```

**Step 4: Reconcile Data Loss (if any)**
- Identify transactions between backup time and corruption
- Attempt to recover from application logs
- Communicate data loss to affected users (if significant)

**Step 5: Restart Services**
```bash
# Start application
sudo systemctl start ralph-bot

# Monitor logs
sudo journalctl -u ralph-bot -f
```

**Step 6: Investigate Root Cause**
- Review logs for errors leading to corruption
- Check disk space and I/O errors
- Verify database configuration
- Test database integrity checks

**Total Recovery Time:** 1-3 hours (depending on database size)

---

### 7.3 Third-Party API Outage (Groq, Telegram)

**Symptoms:**
- API requests timing out or returning errors
- Users unable to interact with bot
- Error logs showing API failures

**Recovery Steps:**

**Step 1: Verify Outage (5 minutes)**
```bash
# Test Groq API
curl -H "Authorization: Bearer $GROQ_API_KEY" \
  https://api.groq.com/openai/v1/models

# Test Telegram API
curl https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe

# Check status pages
# Groq: [Status page URL]
# Telegram: https://t.me/TelegramStatus
```

**Step 2: Implement Fallback (if available)**

**Groq API Outage:**
```python
# Fallback to OpenAI or Anthropic Claude API
try:
    response = groq_client.chat.completions.create(...)
except Exception as e:
    logger.warning(f"Groq API failed: {e}, falling back to OpenAI")
    response = openai_client.chat.completions.create(...)
```

**Telegram API Outage:**
- Enable message queuing (store messages, retry later)
- Display maintenance message on website
- Communicate via email or social media

**Step 3: Monitor for Recovery**
- Check API status every 15 minutes
- Test functionality when API restores
- Gradually resume normal operations

**Step 4: Communicate with Users**
```
⚠️ SERVICE NOTICE

We're experiencing issues with our AI provider [Groq/Telegram].
Our team is monitoring the situation and service will automatically
restore when their API is back online.

Estimated restoration: [Based on vendor status page]
```

**Step 5: Post-Recovery**
- Process queued messages/requests
- Verify all functionality restored
- Document outage duration and impact

**Total Recovery Time:** Dependent on third-party (15 minutes to several hours)

---

### 7.4 Deployment Rollback (Buggy Release)

**Symptoms:**
- Increased error rates after deployment
- User reports of broken functionality
- Performance degradation

**Recovery Steps:**

**Step 1: Detect Issue (5-15 minutes)**
- Monitoring alerts trigger
- Error tracking shows spike (Sentry)
- User reports via support

**Step 2: Assess Severity**
- Is service completely broken? → Immediate rollback
- Is one feature broken? → Consider hotfix vs. rollback
- Is it a performance issue? → Investigate, may need rollback

**Step 3: Rollback to Previous Version**
```bash
# SSH to server
ssh root@69.164.201.191

# Navigate to project directory
cd /root/ralph-starter

# View recent commits
git log --oneline -10

# Rollback to previous commit
git checkout [previous-commit-hash]

# Reinstall dependencies (if changed)
source venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl restart ralph-bot

# Verify functionality
curl http://localhost:8000/health
```

**Step 4: Verify Rollback Success (10 minutes)**
- Test critical user flows
- Check error rates return to normal
- Monitor performance metrics

**Step 5: Communicate**
- Update status page: "Issue resolved via rollback"
- Email users if significant impact
- Internal debrief on what went wrong

**Step 6: Root Cause Analysis**
- Identify bug in rolled-back code
- Create hotfix branch
- Test thoroughly in staging
- Deploy fix when ready

**Total Recovery Time:** 15-30 minutes

---

## 8. Recovery Resources

### 8.1 Required Infrastructure

**Minimum Viable Service:**
- 1× Linode instance (2 GB RAM, 1 CPU, 50 GB storage)
- 1× Database instance (can be on same server initially)
- 1× Domain (ralphmode.com with DNS configured)
- 1× SSL certificate (Let's Encrypt, free)

**Estimated Monthly Cost:** $10-20 (Linode pricing)

**Emergency Budget:**
- Infrastructure scaling: $500 (for handling incidents)
- Third-party support: $1,000 (if expert help needed)
- Communication tools: $100 (SMS, alerts, monitoring)

### 8.2 Required Personnel

**Minimum Team:**
- 1× Technical lead (server management, deployment)
- 1× Developer (code fixes, debugging)
- 1× Communications person (user updates, status page)

**On-Call Coverage:**
- Primary on-call: 24/7 availability
- Secondary on-call: Backup if primary unavailable
- Escalation: CTO for critical (P0) incidents

**Availability Requirements:**
- Acknowledge alerts within 15 minutes
- Begin response within 30 minutes
- Provide updates every 30 minutes (P0) or 60 minutes (P1)

### 8.3 Required Tools and Access

**Immediate Access Required:**
- Linode dashboard login (+ MFA)
- GitHub repository access (SSH key)
- Domain registrar (GoDaddy) login
- Database credentials (from password manager)
- API keys for third-party services
- SSH keys for server access

**Communication Tools:**
- Email access (security@ralphmode.com)
- Slack workspace access
- Status page admin (status.ralphmode.com)
- Social media accounts (Twitter/X)

**Recovery Tools:**
- Backup storage access (S3, Linode Object Storage)
- Monitoring dashboards (UptimeRobot, Sentry)
- Password manager (1Password, Bitwarden)
- Documentation (runbooks, architecture diagrams)

---

## 9. Continuity Testing and Drills

### 9.1 Testing Schedule

**Quarterly (Every 3 Months):**
- Backup restore test (verify backups work)
- Runbook walkthrough (ensure docs are current)
- Contact list verification (phone numbers, emails)

**Semi-Annual (Every 6 Months):**
- Disaster recovery drill (simulate server failure)
- Failover test (if multi-region implemented)
- Communication drill (practice user notifications)

**Annual:**
- Full BCP review and update
- Tabletop exercise (simulate major incident)
- Executive review of continuity readiness

### 9.2 Drill Scenarios

**Drill 1: Database Restore**
```
SCENARIO: Database corruption detected. Restore from most recent backup.

OBJECTIVES:
1. Download latest backup from object storage
2. Restore to test database instance
3. Verify data integrity
4. Document time required

SUCCESS CRITERIA:
- Restore completed in <1 hour
- Data integrity verified (no missing records)
- Application connects successfully to restored DB
```

**Drill 2: Server Failover**
```
SCENARIO: Primary server hardware failure. Restore service on new server.

OBJECTIVES:
1. Provision new Linode instance
2. Restore database from backup
3. Deploy application code
4. Update DNS records
5. Verify functionality

SUCCESS CRITERIA:
- Service restored in <2 hours
- Data loss <1 hour (RPO)
- All critical features functional
```

**Drill 3: Communication Exercise**
```
SCENARIO: Major outage lasting 6+ hours. Practice user communication.

OBJECTIVES:
1. Update status page with incident details
2. Draft and send user notification email
3. Post updates to social media
4. Provide hourly updates until resolution

SUCCESS CRITERIA:
- First communication within 15 minutes
- Updates every 30-60 minutes
- Clear, honest, empathetic messaging
- Users understand what happened and what to expect
```

### 9.3 Drill Documentation

After each drill, document:
- Date and participants
- Scenario executed
- Time to complete each step
- Issues encountered
- Gaps in documentation or tooling
- Action items for improvement

**Example:**
```markdown
# BCP Drill Report: Database Restore

**Date:** 2026-01-15
**Participants:** [Names]
**Scenario:** Database restore from backup

**Timeline:**
- 10:00: Drill initiated
- 10:05: Backup downloaded from S3
- 10:15: Restore command executed
- 10:45: Restore completed
- 10:50: Integrity verified
- **Total: 50 minutes**

**Issues:**
- Backup download slower than expected (10 minutes vs. 2 minutes)
- Restore command not in runbook (had to search documentation)
- Test database credentials not in password manager

**Action Items:**
1. Investigate faster backup storage or compression
2. Add restore commands to runbook
3. Add test DB credentials to 1Password

**Success:** ✅ Restored within 1-hour target
```

---

## 10. Plan Maintenance

### 10.1 Review and Update Schedule

**Quarterly Reviews:**
- Update contact lists (phone numbers, emails)
- Review RTO/RPO targets (still appropriate?)
- Test backup restoration
- Update emergency procedures

**Annual Comprehensive Review:**
- Full BCP walkthrough with all stakeholders
- Update risk assessment
- Review and update recovery procedures
- Test all documented procedures
- Update cost estimates and budgets

**Trigger-Based Updates:**
- After major infrastructure changes
- After business model changes (e.g., paid subscriptions)
- After organizational changes (new team members, departures)
- After actual incidents (incorporate lessons learned)

### 10.2 Change Management

**When BCP Changes Are Needed:**
1. Identify change requirement
2. Document proposed change
3. Review with stakeholders
4. Update BCP document
5. Communicate changes to team
6. Train team on changes
7. Test new procedures

**Version Control:**
- BCP stored in git repository (docs/security/)
- Changes tracked via commits
- Version number incremented (semantic versioning)
- Changelog maintained

---

## 11. Roles and Responsibilities

### 11.1 Executive Leadership

**CTO:**
- BCP ownership and approval
- Emergency decision-making authority
- Resource allocation for recovery
- Executive communication

**CEO (if applicable):**
- Public communication (media, major customers)
- Legal and regulatory liaison
- Board of directors communication

### 11.2 Operations Team

**On-Call Engineer:**
- 24/7 incident response
- Execute recovery procedures
- Coordinate with team
- Document incident timeline

**DevOps Lead:**
- Infrastructure recovery
- Backup management
- System hardening post-incident

**Database Administrator:**
- Database backup and recovery
- Data integrity verification
- Performance tuning post-recovery

### 11.3 Development Team

**Senior Developers:**
- Code deployment and rollback
- Bug fixes and hotfixes
- Testing and verification

**Junior Developers:**
- Support during incidents
- Documentation updates
- Testing assistance

### 11.4 Support and Communication

**Customer Support:**
- Monitor user reports
- Provide updates to users
- Escalate critical issues

**Communications Lead:**
- Status page updates
- User email communications
- Social media updates
- Media relations (if needed)

---

## 12. Related Plans and Documents

- **Security Incident Response Plan:** For security-specific incidents
- **Disaster Recovery Plan:** Detailed technical recovery procedures
- **Information Security Policy:** Overall security framework
- **Access Control Policy:** Emergency access procedures
- **Data Classification Policy:** Backup and recovery requirements by data type

---

## 13. Appendices

### Appendix A: Quick Reference Checklist

**Server Down - Quick Recovery Steps:**
1. [ ] Verify outage (ping, curl, SSH)
2. [ ] Alert team (Slack #incidents)
3. [ ] Update status page (status.ralphmode.com)
4. [ ] Attempt server reboot (via Linode dashboard)
5. [ ] If reboot fails, provision new server
6. [ ] Restore database from latest backup
7. [ ] Deploy application code (git clone)
8. [ ] Update DNS A record to new IP
9. [ ] Test functionality
10. [ ] Announce restoration
11. [ ] Document incident

**Estimated Time:** 1-2 hours

---

### Appendix B: Emergency Contacts (Template)

| Role | Name | Phone | Email | Backup |
|------|------|-------|-------|--------|
| CTO | [Name] | [Phone] | [Email] | [Name] |
| On-Call (Week 1) | [Name] | [Phone] | [Email] | [Name] |
| On-Call (Week 2) | [Name] | [Phone] | [Email] | [Name] |
| DevOps Lead | [Name] | [Phone] | [Email] | [Name] |
| Comms Lead | [Name] | [Phone] | [Email] | [Name] |

**External:**
| Service | Contact | Phone | Email/URL |
|---------|---------|-------|-----------|
| Linode | Support | - | https://www.linode.com/support |
| GoDaddy | Support | 480-505-8877 | https://www.godaddy.com/contact-us |
| Groq | Support | - | [Support email] |

---

### Appendix C: Recovery Runbooks

**Runbook: Restore Database from Backup**

```bash
#!/bin/bash
# Database restoration runbook

# 1. Download latest backup
aws s3 cp s3://ralphmode-backups/latest.sql /tmp/restore.sql

# 2. Stop application
sudo systemctl stop ralph-bot

# 3. Backup current database (just in case)
pg_dump ralphmode > /tmp/current_backup_$(date +%Y%m%d_%H%M%S).sql

# 4. Drop and recreate database
sudo -u postgres psql -c "DROP DATABASE ralphmode;"
sudo -u postgres psql -c "CREATE DATABASE ralphmode;"

# 5. Restore from backup
sudo -u postgres psql ralphmode < /tmp/restore.sql

# 6. Verify
sudo -u postgres psql -d ralphmode -c "SELECT COUNT(*) FROM users;"

# 7. Restart application
sudo systemctl start ralph-bot

# 8. Monitor logs
sudo journalctl -u ralph-bot -f
```

---

**Runbook: Provision New Linode Server**

```bash
# Via Linode dashboard (manual steps):
1. Click "Create Linode"
2. Select: Ubuntu 22.04 LTS
3. Size: Shared CPU, Linode 2GB ($10/month)
4. Region: Same as original (or failover region)
5. Label: ralphmode-production-[date]
6. Root password: [Generate strong password]
7. SSH keys: Add your public key
8. Click "Create Linode"
9. Wait ~1 minute for provisioning

# Initial server setup:
ssh root@[NEW_IP]

apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git nginx certbot

# Clone repository
git clone https://github.com/Snail3D/ralphmode.com.git
cd ralphmode.com/ralph-starter

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Restore .env file
nano .env
# Paste secrets from password manager

# Restore database (see database restore runbook)

# Start service
sudo systemctl start ralph-bot
sudo systemctl enable ralph-bot

# Update DNS
# Go to GoDaddy DNS management
# Update A record: @ -> [NEW_IP]
# Update A record: www -> [NEW_IP]

# Wait 10-15 minutes for DNS propagation
# Test: curl https://ralphmode.com
```

---

### Appendix D: Backup Verification Log (Template)

```markdown
# Monthly Backup Verification Log

**Date:** [YYYY-MM-DD]
**Performed By:** [Name]
**Backup Tested:** [Backup file name and date]

## Steps Performed
1. [ ] Downloaded backup from object storage
2. [ ] Restored to test database instance
3. [ ] Verified row counts match expected values
4. [ ] Tested application connection to restored DB
5. [ ] Verified data integrity (sample records)

## Results
- Backup file size: [XX MB]
- Restoration time: [XX minutes]
- Row counts verified: ✅ / ❌
- Sample data verified: ✅ / ❌
- Application connection: ✅ / ❌

## Issues Encountered
[None / Description of issues]

## Action Items
[None / List of follow-up actions]

**Sign-off:** [Name], [Date]
```

---

## 14. Approval and Acknowledgment

This Business Continuity Plan has been reviewed and approved by:

- **Chief Technology Officer:** [Name], [Date]
- **Chief Executive Officer:** [Name], [Date] (if applicable)
- **Operations Lead:** [Name], [Date]
- **Security Lead:** [Name], [Date]

**Effective Date:** January 2026
**Next Review Date:** January 2027

---

**For questions or updates to this plan, contact:** ops@ralphmode.com

**Version History:**
- v1.0 (January 2026): Initial release
