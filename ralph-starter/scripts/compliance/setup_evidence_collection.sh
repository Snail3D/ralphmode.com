#!/bin/bash
#
# SOC 2 Evidence Collection - Cron Setup
#
# This script sets up automated evidence collection for SOC 2 compliance.
# Run once to install the cron job.
#
# Usage: sudo ./setup_evidence_collection.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EVIDENCE_SCRIPT="$SCRIPT_DIR/evidence_collector.py"

echo "=== SOC 2 Evidence Collection Setup ==="
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

# Verify evidence collector script exists
if [ ! -f "$EVIDENCE_SCRIPT" ]; then
    echo "ERROR: Evidence collector script not found: $EVIDENCE_SCRIPT"
    exit 1
fi

# Make evidence collector executable
chmod +x "$EVIDENCE_SCRIPT"
echo "✓ Evidence collector script is executable"

# Create log directory
mkdir -p /var/log
touch /var/log/evidence_collector.log
chmod 644 /var/log/evidence_collector.log
echo "✓ Log file created: /var/log/evidence_collector.log"

# Create evidence directory
mkdir -p "$PROJECT_ROOT/evidence/soc2"
chmod 755 "$PROJECT_ROOT/evidence/soc2"
echo "✓ Evidence directory created: $PROJECT_ROOT/evidence/soc2"

# Add cron job (daily at 2 AM)
CRON_JOB="0 2 * * * cd $PROJECT_ROOT && /usr/bin/python3 $EVIDENCE_SCRIPT >> /var/log/evidence_collector.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$EVIDENCE_SCRIPT"; then
    echo "✓ Cron job already exists"
else
    # Add cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✓ Cron job added: Daily at 2 AM"
fi

# Display current crontab
echo
echo "Current crontab:"
crontab -l | grep "$EVIDENCE_SCRIPT" || echo "(no evidence collection jobs)"

echo
echo "=== Setup Complete ==="
echo
echo "Evidence will be collected daily at 2 AM"
echo "Logs: /var/log/evidence_collector.log"
echo "Evidence: $PROJECT_ROOT/evidence/soc2/"
echo
echo "To run manually: sudo python3 $EVIDENCE_SCRIPT"
echo "To view logs: tail -f /var/log/evidence_collector.log"
echo
