# SEC-014: DDoS Protection for Ralph Mode

## Overview

This document describes the comprehensive DDoS protection implementation for Ralph Mode, covering infrastructure setup, monitoring, and incident response.

## Protection Layers

Ralph Mode implements defense-in-depth for DDoS protection:

```
Internet
    ↓
┌─────────────────────────────────────┐
│   Cloudflare (L3/L4/L7 Protection)  │  ← Primary DDoS mitigation
├─────────────────────────────────────┤
│   - Anycast DNS                     │
│   - Bot detection                   │
│   - Rate limiting                   │
│   - WAF rules                       │
│   - Challenge pages                 │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│   Nginx (Reverse Proxy)             │  ← Application-level protection
├─────────────────────────────────────┤
│   - Connection limits               │
│   - Request rate limits             │
│   - Security headers                │
│   - SSL/TLS termination             │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│   Application Rate Limiter          │  ← Endpoint-specific limits
├─────────────────────────────────────┤
│   - Per-IP limits (1000/min)        │
│   - Per-user limits                 │
│   - Auth endpoints (10/min)         │
│   - Redis-backed                    │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│   Origin Server (Linode)            │  ← Hidden behind CDN
├─────────────────────────────────────┤
│   - Firewall (Cloudflare IPs only)  │
│   - No direct public access         │
│   - IP: 69.164.201.191 (hidden)     │
└─────────────────────────────────────┘
```

## Layer 3/4 Protection (Network Layer)

**Threat:** SYN floods, UDP floods, ICMP floods, amplification attacks

**Mitigation:**
- Cloudflare Anycast network absorbs volumetric attacks
- Automatic detection and mitigation (no configuration needed)
- Capacity: Multi-Tbps mitigation capability
- Hidden origin IP prevents direct attacks

**Status:** ✅ Automatic (enabled when using Cloudflare proxy)

## Layer 7 Protection (Application Layer)

**Threat:** HTTP floods, Slowloris, application exhaustion

**Mitigation:**

### 1. Cloudflare Rate Limiting
```json
{
  "global": "1000 req/min per IP",
  "auth_endpoints": "10 req/min per IP",
  "api_endpoints": "100 req/min per IP"
}
```

### 2. Bot Detection
- Bot Fight Mode: Blocks known malicious bots
- Super Bot Fight Mode: ML-based detection (Business plan)
- Challenge suspicious traffic with JavaScript/CAPTCHA

### 3. Web Application Firewall (WAF)
- Cloudflare Managed Ruleset
- OWASP Core Rule Set
- Custom rules for SQL injection, XSS, etc.

### 4. Challenge Pages
- JavaScript challenge for suspicious IPs
- CAPTCHA for high-risk traffic
- "Under Attack Mode" for active DDoS

## Traffic Spike Alerting

### Monitoring
- **Cloudflare Analytics:** Real-time traffic dashboard
- **Threshold:** 5x normal baseline triggers alert
- **Baseline Window:** 7-day rolling average
- **Metrics:**
  - Requests per second
  - Bandwidth usage
  - Threat score distribution
  - Bot traffic percentage
  - Geographic distribution

### Alert Channels
1. **Email:** alerts@ralphmode.com
2. **Webhook:** https://ralphmode.com/api/cloudflare-webhook
3. **Dashboard:** Cloudflare Analytics

### Alert Triggers
- Traffic spike (5x baseline)
- High threat score events
- Origin server unreachable
- SSL certificate expiring
- Firewall rule hits

## Bot Detection & Mitigation

### Known Malicious Bots
- **Action:** Automatic block
- **Detection:** Cloudflare threat intelligence
- **Updates:** Continuous from global network

### Verified Good Bots
- **Allowed:** Googlebot, Bingbot, Slackbot, etc.
- **No Challenge:** Bypass JavaScript challenges
- **Verification:** DNS verification + user agent

### Suspicious Bots
- **Action:** JavaScript challenge
- **Detection:** Behavioral analysis, headers, fingerprints
- **Pass Rate:** Legitimate browsers pass, bots fail

### Configuration
```javascript
// Bot Fight Mode (Free plan)
bot_fight_mode: true

// Super Bot Fight Mode (Business plan)
super_bot_fight_mode: {
  enabled: true,
  action: "challenge",
  detect_anomalies: true
}
```

## Anycast DNS for Distributed Entry

**What is Anycast?**
- Same IP address announced from multiple locations worldwide
- Traffic routed to nearest/healthiest Cloudflare data center
- Automatic failover if data center goes down

**Benefits:**
- Low latency (geographically distributed)
- High availability (no single point of failure)
- DDoS absorption (distribute attack across network)

**Implementation:**
- Cloudflare provides this automatically
- No configuration required
- Works for both IPv4 and IPv6

**Nameservers:**
```
ns1.cloudflare.com
ns2.cloudflare.com
```

## Origin IP Protection

### Why Hide Origin IP?

If attackers know your origin server IP (69.164.201.191), they can bypass Cloudflare and attack you directly.

### How We Hide It

1. **DNS Proxying**
   - A records proxied through Cloudflare (orange cloud)
   - DNS queries return Cloudflare IPs, not origin IP
   - Origin IP never exposed in public DNS

2. **Firewall at Origin**
   - Only allow connections from Cloudflare IP ranges
   - Block all other IPs (including direct connections)
   - Update rules regularly as Cloudflare IPs change

3. **Authenticated Origin Pulls**
   - Require Cloudflare client certificate
   - Nginx validates certificate before accepting connection
   - Prevents IP spoofing attacks

4. **Security Best Practices**
   - Never commit origin IP to public repos (too late, already public, but don't leak again)
   - Don't expose origin IP in error messages
   - Don't allow outbound connections that leak origin IP
   - Use Cloudflare-provided origin certificate

### Firewall Configuration (Linode)

```bash
# Download Cloudflare IP ranges
curl https://www.cloudflare.com/ips-v4 -o /tmp/cf-ips-v4.txt
curl https://www.cloudflare.com/ips-v6 -o /tmp/cf-ips-v6.txt

# Configure UFW to only allow Cloudflare
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp  # SSH - restrict to your IP in production

# Allow Cloudflare IPs only for HTTP/HTTPS
for ip in $(cat /tmp/cf-ips-v4.txt); do
  ufw allow from $ip to any port 80 proto tcp
  ufw allow from $ip to any port 443 proto tcp
done

ufw enable
```

### Origin Certificate Setup

```bash
# Generate Cloudflare Origin Certificate in dashboard
# Download certificate and key
# Install on nginx

# /etc/nginx/sites-available/ralphmode.com
ssl_certificate /etc/ssl/cloudflare/origin-cert.pem;
ssl_certificate_key /etc/ssl/cloudflare/origin-key.pem;

# Require Cloudflare client certificate
ssl_client_certificate /etc/ssl/cloudflare/origin-pull-ca.pem;
ssl_verify_client on;
```

## Geo-Blocking (Optional)

**Status:** Disabled by default

**Why?** Most applications should serve global users. Geo-blocking can affect legitimate users and VPN traffic.

**When to Enable:**
- Compliance requirements (GDPR, export controls)
- Known attack sources from specific regions
- Business model is region-specific

**Configuration:**
```json
{
  "geo_blocking": {
    "enabled": false,
    "action": "challenge",  // or "block"
    "countries": []  // ISO country codes
  }
}
```

**Recommendation:** Use "challenge" instead of "block" to allow legitimate users through CAPTCHA.

## Under Attack Mode

### What Is It?
Emergency mode that shows JavaScript challenge to ALL visitors. Very aggressive protection for active DDoS attacks.

### When to Enable
- Active DDoS attack in progress
- Traffic spikes overwhelming origin server
- Sustained bot attacks that bypass normal challenges
- Layer 7 HTTP floods

### How to Enable
**Option 1: Cloudflare Dashboard**
```
Security → Settings → Security Level → I'm Under Attack
```

**Option 2: Cloudflare API**
```bash
curl -X PATCH "https://api.cloudflare.com/client/v4/zones/{zone_id}/settings/security_level" \
  -H "Authorization: Bearer {api_token}" \
  -H "Content-Type: application/json" \
  --data '{"value":"under_attack"}'
```

**Option 3: Page Rule**
Create page rule to enable for specific URLs only:
```
URL: ralphmode.com/api/*
Security Level: I'm Under Attack
```

### Trade-offs
**Pros:**
- ✅ Blocks most automated attacks
- ✅ Protects origin from being overwhelmed
- ✅ Easy to enable/disable

**Cons:**
- ❌ All visitors see challenge page (5-second delay)
- ❌ Breaks API clients that don't execute JavaScript
- ❌ Inconveniences legitimate users
- ❌ May reduce conversions/engagement

### Best Practices
- Use temporarily during active attacks only
- Disable when traffic normalizes
- Consider Page Rules to only protect specific paths
- Communicate to users via status page

## Testing DDoS Protection

### Pre-Deployment Tests

1. **Verify Cloudflare Proxy**
   ```bash
   dig ralphmode.com
   # Should return Cloudflare IPs, not 69.164.201.191
   ```

2. **Test Origin Firewall**
   ```bash
   # Direct connection to origin should fail
   curl -I http://69.164.201.191
   # Connection refused or timeout

   # Connection via Cloudflare should work
   curl -I https://ralphmode.com
   # 200 OK
   ```

3. **Test Rate Limiting**
   ```bash
   # Rapid requests should trigger rate limit
   for i in {1..100}; do
     curl https://ralphmode.com/api/auth/login
   done
   # Should see 429 Too Many Requests
   ```

4. **Test Challenge Page**
   ```bash
   # Enable "Under Attack Mode"
   # Visit https://ralphmode.com in browser
   # Should see JavaScript challenge
   ```

5. **Test Bot Detection**
   ```bash
   # Request with no user agent (bot behavior)
   curl -A "" https://ralphmode.com
   # Should get challenged or blocked
   ```

### Load Testing (Do NOT run against production)

⚠️ **WARNING:** Load testing production infrastructure can trigger actual DDoS mitigation and affect real users. Only test against staging/dev environments.

**Approved Load Testing:**
- Use Cloudflare's official load testing tools
- Coordinate with Cloudflare support for planned tests
- Use staging environment with separate domain
- Whitelist your IPs during testing

**Tools:**
- Apache Bench (ab)
- wrk
- Locust
- k6

**Example (staging only):**
```bash
# Simple load test with Apache Bench
ab -n 10000 -c 100 https://staging.ralphmode.com/

# Monitor:
# - Response times
# - Error rates
# - Cloudflare Analytics
# - Origin server load
```

## Incident Response Playbook

### DDoS Attack Detected

**Phase 1: Confirm Attack (< 5 minutes)**

1. Check Cloudflare Analytics
   - Traffic spike vs. baseline?
   - High threat score events?
   - Abnormal geographic distribution?

2. Check Origin Server
   - CPU/memory usage normal?
   - Origin responding to health checks?
   - Application errors in logs?

3. Identify Attack Type
   - L3/L4: Cloudflare auto-mitigates (no action needed)
   - L7 HTTP flood: May need "Under Attack Mode"
   - Targeted endpoint: May need custom firewall rule

**Phase 2: Mitigate (< 15 minutes)**

**If origin is healthy:** Cloudflare is handling it ✅
- Monitor analytics
- No action needed

**If origin is struggling:**
1. Enable "Under Attack Mode" (immediate relief)
   - Security → Settings → I'm Under Attack
2. Add rate limiting rules for affected endpoints
3. Create firewall rules to block attack patterns
4. Consider geo-blocking if attack is region-specific

**If origin is down:**
1. Enable "Under Attack Mode"
2. Check origin server health
3. Restart services if needed
4. Verify firewall rules (Cloudflare IPs allowed?)
5. Check nginx error logs

**Phase 3: Analyze (< 1 hour)**

1. Review Cloudflare Firewall Events
   - What IPs/countries?
   - What endpoints targeted?
   - What patterns?

2. Create targeted firewall rules
   ```
   Block: (ip.src in {attacker_ips})
   Challenge: (http.request.uri.path eq "/targeted/endpoint")
   ```

3. Export logs for forensics
   - Cloudflare Logpush (Enterprise)
   - Or manual export from Analytics

**Phase 4: Recovery (< 2 hours)**

1. Verify attack has subsided
   - Traffic returns to baseline
   - Threat scores normal
   - Origin server healthy

2. Gradually reduce restrictions
   - Disable "Under Attack Mode"
   - Relax custom firewall rules (keep monitoring)
   - Return to normal security level

3. Document incident
   - Timeline
   - Attack vectors
   - Mitigation steps
   - Lessons learned

4. Update playbook
   - What worked?
   - What didn't?
   - How to respond faster next time?

### Escalation

**Cloudflare Support:**
- Free plan: Community forums only
- Pro plan ($20/mo): Email support (within 24h)
- Business plan ($200/mo): Priority support (within 2h)
- Enterprise: Dedicated support (immediate)

**When to Escalate:**
- Attack > 10 Gbps (may need Enterprise plan)
- Novel attack vectors not being mitigated
- Need custom WAF rules
- Compliance/legal requirements

**Contact:**
- Support: https://dash.cloudflare.com/support
- Emergency (Enterprise): 24/7 phone hotline

## Monitoring Dashboard

### Key Metrics

1. **Requests Per Second**
   - Baseline: ~10-100 RPS (varies by traffic)
   - Alert Threshold: 5x baseline
   - Under Attack: Can spike to 10,000+ RPS

2. **Bandwidth**
   - Baseline: ~1-10 GB/day
   - Alert Threshold: 5x baseline
   - Cloudflare absorbs attack traffic (doesn't count against origin)

3. **Threat Score**
   - 0-10: Legitimate traffic ✅
   - 10-30: Suspicious, may challenge
   - 30+: High risk, block/challenge aggressively

4. **Bot Traffic %**
   - Normal: 20-40% (search engines, monitoring)
   - Under Attack: 80-100% malicious bots

5. **Cache Hit Ratio**
   - Target: >80% for static content
   - Low ratio = more load on origin
   - Improves DDoS resilience

### Cloudflare Analytics Dashboard

**Access:** https://dash.cloudflare.com → Analytics

**Widgets:**
- Traffic graph (last 24h, 7d, 30d)
- Requests by country
- Threats mitigated
- Bot traffic
- Top crawlers
- Cache performance
- SSL/TLS versions
- HTTP status codes

**Firewall Events:**
- Security → Overview → Firewall Events
- Filter by: action, country, IP, user agent
- Export to CSV for analysis

## Cost Analysis

### Cloudflare Plans

| Plan | Cost | DDoS Protection | Best For |
|------|------|-----------------|----------|
| **Free** | $0/mo | ✅ Unlimited L3/L4/L7 | Most sites (Ralph Mode START HERE) |
| **Pro** | $20/mo | ✅ + WAF + Better analytics | Production apps |
| **Business** | $200/mo | ✅ + Advanced DDoS + 24/7 support | E-commerce, high-value targets |
| **Enterprise** | Custom | ✅ + Dedicated support + Custom rules | Large enterprises |

### Recommendation for Ralph Mode

**Start with Free:**
- Covers 99% of DDoS attacks
- Unlimited mitigation capacity
- Bot detection included
- Good enough for MVP to 10,000 users

**Upgrade to Pro when:**
- Need WAF for advanced security
- Want better analytics
- Need more page rules (20 vs 3)
- Revenue > $100/month (justify $20 cost)

**Upgrade to Business when:**
- Revenue > $1,000/month
- Handling payments (PCI-DSS)
- Need 24/7 support SLA
- Target of sophisticated attacks

## Compliance

### PCI-DSS
- Cloudflare Business plan required
- WAF helps meet requirement 6.6
- DDoS protection meets requirement 10.5.5
- Contact Cloudflare for AOC (Attestation of Compliance)

### GDPR
- Cloudflare is GDPR compliant
- Data Processing Addendum (DPA) available
- EU data centers available
- Privacy controls in dashboard

### HIPAA
- Requires Cloudflare Enterprise + BAA
- Not applicable to Ralph Mode (no PHI)

### SOC 2
- Cloudflare is SOC 2 Type II certified
- Audit reports available to Enterprise customers

## Maintenance

### Weekly
- [ ] Review Cloudflare Analytics for anomalies
- [ ] Check threat score trends
- [ ] Verify origin server health

### Monthly
- [ ] Update Cloudflare IP allowlist on origin firewall
  ```bash
  curl https://www.cloudflare.com/ips-v4 -o /tmp/cf-ips-v4.txt
  # Compare with current firewall rules
  # Update if changed
  ```
- [ ] Review firewall rules for effectiveness
- [ ] Check SSL certificate expiration (90 days for Let's Encrypt)
- [ ] Review rate limiting rules (too strict? too loose?)

### Quarterly
- [ ] Review and test incident response playbook
- [ ] Evaluate Cloudflare plan (upgrade needed?)
- [ ] Audit firewall rules (remove unused)
- [ ] Performance review (cache hit ratio, etc.)

### Annually
- [ ] Full DDoS protection audit
- [ ] Review threat landscape changes
- [ ] Update security policies
- [ ] Team training on incident response

## References

- [Cloudflare DDoS Protection Docs](https://developers.cloudflare.com/ddos-protection/)
- [Cloudflare IP Ranges](https://www.cloudflare.com/ips/)
- [Cloudflare Rate Limiting](https://developers.cloudflare.com/waf/rate-limiting-rules/)
- [Cloudflare Firewall Rules](https://developers.cloudflare.com/firewall/)
- [Cloudflare Analytics](https://developers.cloudflare.com/analytics/)
- [OWASP DDoS Prevention](https://owasp.org/www-community/attacks/Denial_of_Service)

## Quick Reference Card

```
🚨 UNDER DDOS ATTACK? 🚨

1. Go to: https://dash.cloudflare.com
2. Security → Settings → Security Level → I'm Under Attack
3. Monitor: Analytics → Traffic graph
4. When stable: Revert to High security level

Emergency Contact:
- Cloudflare Support: https://dash.cloudflare.com/support
- Origin Server SSH: ssh root@69.164.201.191
- Monitoring: Cloudflare Analytics Dashboard

Key Commands:
- Check DNS: dig ralphmode.com
- Test origin: curl -I http://69.164.201.191
- Check firewall: sudo ufw status
- Nginx logs: sudo tail -f /var/log/nginx/ralphmode.error.log
```

---

**Last Updated:** 2026-01-10
**Owner:** Ralph Mode Security Team
**Classification:** Public (but don't advertise our defenses)
