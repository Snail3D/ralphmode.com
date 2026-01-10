#!/bin/bash
#
# SEC-014: Origin Server Firewall Setup
#
# This script configures UFW (Uncomplicated Firewall) to only allow
# traffic from Cloudflare IP ranges, effectively hiding the origin
# server from direct attacks.
#
# WARNING: This will block all non-Cloudflare traffic!
# Make sure Cloudflare is properly configured before running.
#
# Usage:
#   sudo ./setup_origin_firewall.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}SEC-014: Cloudflare Origin Firewall Setup${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}ERROR: This script must be run as root${NC}"
   echo "Usage: sudo $0"
   exit 1
fi

# Check if UFW is installed
if ! command -v ufw &> /dev/null; then
    echo -e "${YELLOW}UFW not found. Installing...${NC}"
    apt-get update
    apt-get install -y ufw
fi

echo -e "${YELLOW}⚠️  WARNING: This will configure firewall to ONLY allow Cloudflare IPs${NC}"
echo -e "${YELLOW}   Make sure Cloudflare is properly set up before continuing!${NC}"
echo ""
read -p "Continue? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo -e "${GREEN}Step 1: Downloading Cloudflare IP ranges...${NC}"

# Download Cloudflare IPv4 ranges
echo "Downloading IPv4 ranges..."
if ! curl -s https://www.cloudflare.com/ips-v4 -o /tmp/cf-ips-v4.txt; then
    echo -e "${RED}ERROR: Failed to download Cloudflare IPv4 ranges${NC}"
    exit 1
fi

# Download Cloudflare IPv6 ranges
echo "Downloading IPv6 ranges..."
if ! curl -s https://www.cloudflare.com/ips-v6 -o /tmp/cf-ips-v6.txt; then
    echo -e "${RED}ERROR: Failed to download Cloudflare IPv6 ranges${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Downloaded Cloudflare IP ranges${NC}"
echo "   IPv4 ranges: $(wc -l < /tmp/cf-ips-v4.txt) ranges"
echo "   IPv6 ranges: $(wc -l < /tmp/cf-ips-v6.txt) ranges"
echo ""

# Backup current UFW rules
echo -e "${GREEN}Step 2: Backing up current firewall rules...${NC}"
ufw status numbered > /tmp/ufw-backup-$(date +%Y%m%d-%H%M%S).txt || true
echo -e "${GREEN}✅ Backup saved to /tmp/ufw-backup-*.txt${NC}"
echo ""

# Reset UFW (optional - comment out if you want to preserve existing rules)
echo -e "${GREEN}Step 3: Configuring UFW defaults...${NC}"
echo "Setting default policies..."
ufw --force default deny incoming
ufw --force default allow outgoing
echo -e "${GREEN}✅ Default policies set${NC}"
echo ""

# Allow SSH (customize the IP if you want to restrict SSH access)
echo -e "${GREEN}Step 4: Allowing SSH access...${NC}"
read -p "Restrict SSH to specific IP? (leave blank for any IP): " SSH_IP
if [ -z "$SSH_IP" ]; then
    ufw allow 22/tcp comment 'SSH - All IPs'
    echo -e "${YELLOW}⚠️  SSH allowed from ANY IP (not recommended for production)${NC}"
else
    ufw allow from $SSH_IP to any port 22 proto tcp comment 'SSH - Restricted IP'
    echo -e "${GREEN}✅ SSH allowed only from $SSH_IP${NC}"
fi
echo ""

# Allow Cloudflare IPs for HTTP (port 80)
echo -e "${GREEN}Step 5: Allowing Cloudflare IPs for HTTP (port 80)...${NC}"
IPV4_COUNT=0
while IFS= read -r ip; do
    ufw allow from $ip to any port 80 proto tcp comment 'Cloudflare HTTP'
    ((IPV4_COUNT++))
done < /tmp/cf-ips-v4.txt
echo -e "${GREEN}✅ Added $IPV4_COUNT IPv4 rules for HTTP${NC}"

IPV6_COUNT=0
while IFS= read -r ip; do
    ufw allow from $ip to any port 80 proto tcp comment 'Cloudflare HTTP'
    ((IPV6_COUNT++))
done < /tmp/cf-ips-v6.txt
echo -e "${GREEN}✅ Added $IPV6_COUNT IPv6 rules for HTTP${NC}"
echo ""

# Allow Cloudflare IPs for HTTPS (port 443)
echo -e "${GREEN}Step 6: Allowing Cloudflare IPs for HTTPS (port 443)...${NC}"
IPV4_COUNT=0
while IFS= read -r ip; do
    ufw allow from $ip to any port 443 proto tcp comment 'Cloudflare HTTPS'
    ((IPV4_COUNT++))
done < /tmp/cf-ips-v4.txt
echo -e "${GREEN}✅ Added $IPV4_COUNT IPv4 rules for HTTPS${NC}"

IPV6_COUNT=0
while IFS= read -r ip; do
    ufw allow from $ip to any port 443 proto tcp comment 'Cloudflare HTTPS'
    ((IPV6_COUNT++))
done < /tmp/cf-ips-v6.txt
echo -e "${GREEN}✅ Added $IPV6_COUNT IPv6 rules for HTTPS${NC}"
echo ""

# Enable UFW
echo -e "${GREEN}Step 7: Enabling UFW...${NC}"
echo "y" | ufw enable

echo -e "${GREEN}✅ UFW enabled${NC}"
echo ""

# Show status
echo -e "${GREEN}Step 8: Firewall Status${NC}"
ufw status verbose
echo ""

# Save IP ranges for future updates
echo -e "${GREEN}Step 9: Saving IP ranges for updates...${NC}"
mkdir -p /etc/cloudflare
cp /tmp/cf-ips-v4.txt /etc/cloudflare/ips-v4.txt
cp /tmp/cf-ips-v6.txt /etc/cloudflare/ips-v6.txt
echo -e "${GREEN}✅ IP ranges saved to /etc/cloudflare/${NC}"
echo ""

# Create update script
echo -e "${GREEN}Step 10: Creating update script...${NC}"
cat > /usr/local/bin/update-cloudflare-firewall.sh <<'EOF'
#!/bin/bash
#
# Update Cloudflare firewall rules
# Run this monthly to keep IP ranges current
#

set -e

echo "Updating Cloudflare IP ranges..."

# Download new ranges
curl -s https://www.cloudflare.com/ips-v4 -o /tmp/cf-ips-v4-new.txt
curl -s https://www.cloudflare.com/ips-v6 -o /tmp/cf-ips-v6-new.txt

# Check if ranges changed
if ! diff -q /etc/cloudflare/ips-v4.txt /tmp/cf-ips-v4-new.txt > /dev/null 2>&1 || \
   ! diff -q /etc/cloudflare/ips-v6.txt /tmp/cf-ips-v6-new.txt > /dev/null 2>&1; then

    echo "Cloudflare IP ranges have changed!"
    echo "Updating firewall rules..."

    # Remove old Cloudflare rules
    ufw status numbered | grep 'Cloudflare' | awk '{print $1}' | sed 's/\[\([0-9]*\)\]/\1/' | tac | while read rule_num; do
        echo "y" | ufw delete $rule_num
    done

    # Add new rules (HTTP)
    while IFS= read -r ip; do
        ufw allow from $ip to any port 80 proto tcp comment 'Cloudflare HTTP'
    done < /tmp/cf-ips-v4-new.txt

    while IFS= read -r ip; do
        ufw allow from $ip to any port 80 proto tcp comment 'Cloudflare HTTP'
    done < /tmp/cf-ips-v6-new.txt

    # Add new rules (HTTPS)
    while IFS= read -r ip; do
        ufw allow from $ip to any port 443 proto tcp comment 'Cloudflare HTTPS'
    done < /tmp/cf-ips-v4-new.txt

    while IFS= read -r ip; do
        ufw allow from $ip to any port 443 proto tcp comment 'Cloudflare HTTPS'
    done < /tmp/cf-ips-v6-new.txt

    # Save new ranges
    mv /tmp/cf-ips-v4-new.txt /etc/cloudflare/ips-v4.txt
    mv /tmp/cf-ips-v6-new.txt /etc/cloudflare/ips-v6.txt

    echo "✅ Firewall rules updated"
    ufw reload
else
    echo "✅ Cloudflare IP ranges unchanged"
fi
EOF

chmod +x /usr/local/bin/update-cloudflare-firewall.sh
echo -e "${GREEN}✅ Update script created: /usr/local/bin/update-cloudflare-firewall.sh${NC}"
echo ""

# Create cron job for monthly updates
echo -e "${GREEN}Step 11: Setting up monthly updates...${NC}"
(crontab -l 2>/dev/null | grep -v update-cloudflare-firewall; echo "0 3 1 * * /usr/local/bin/update-cloudflare-firewall.sh >> /var/log/cloudflare-firewall-update.log 2>&1") | crontab -
echo -e "${GREEN}✅ Cron job created (runs 1st of each month at 3 AM)${NC}"
echo ""

# Test connectivity
echo -e "${GREEN}Step 12: Testing configuration...${NC}"
echo "Testing localhost..."
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:80 || echo -e "${YELLOW}⚠️  No web server running on port 80${NC}"
echo ""

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}✅ Firewall setup complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "${YELLOW}IMPORTANT:${NC}"
echo "1. Your origin server is now ONLY accessible via Cloudflare"
echo "2. Direct connections to http://69.164.201.191 will be blocked"
echo "3. Make sure Cloudflare DNS is configured correctly!"
echo "4. To update firewall rules: sudo /usr/local/bin/update-cloudflare-firewall.sh"
echo "5. To check firewall status: sudo ufw status verbose"
echo ""
echo -e "${YELLOW}Testing:${NC}"
echo "- From outside: dig ralphmode.com (should show Cloudflare IPs)"
echo "- From browser: https://ralphmode.com (should work)"
echo "- Direct IP: http://69.164.201.191 (should FAIL - this is good!)"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Test that ralphmode.com works via Cloudflare"
echo "2. Verify direct IP access is blocked"
echo "3. Set up Cloudflare analytics monitoring"
echo "4. Enable 'Under Attack Mode' if needed"
echo ""
