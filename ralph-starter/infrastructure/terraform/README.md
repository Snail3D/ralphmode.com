# SEC-015: Network Segmentation Infrastructure

This directory contains Terraform configurations for implementing network segmentation following security best practices.

## Architecture Overview

```
Internet
    │
    ├─[Cloudflare CDN]─→ WAF, DDoS Protection
    │
    ↓
┌────────────────────────────────────────────┐
│         VPC (10.0.0.0/16)                  │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │  Public Subnet (10.0.1.0/24)         │ │
│  │  - Load Balancer / Nginx Proxy       │ │
│  │  - NAT Gateway                        │ │
│  │  - Bastion Host (SSH access)         │ │
│  └──────────────────────────────────────┘ │
│                  │                         │
│                  ↓                         │
│  ┌──────────────────────────────────────┐ │
│  │  Private Subnet (10.0.2.0/24)        │ │
│  │  - Application Servers               │ │
│  │  - Ralph Bot                          │ │
│  │  - API Server                         │ │
│  │  - No direct internet access          │ │
│  └──────────────────────────────────────┘ │
│                  │                         │
│                  ↓                         │
│  ┌──────────────────────────────────────┐ │
│  │  Database Subnet (10.0.3.0/24)       │ │
│  │  - PostgreSQL / SQLite                │ │
│  │  - Redis Cache                        │ │
│  │  - Completely isolated                │ │
│  │  - No internet access (in or out)     │ │
│  └──────────────────────────────────────┘ │
│                                            │
└────────────────────────────────────────────┘
```

## Security Groups

### Load Balancer Security Group
- **Inbound:** 80 (HTTP), 443 (HTTPS) from Cloudflare IPs only
- **Outbound:** 8080 to App Servers

### Application Server Security Group
- **Inbound:** 8080 from Load Balancer only
- **Outbound:** 5432 to Database, 443 to internet (for APIs)

### Database Security Group
- **Inbound:** 5432 (PostgreSQL), 6379 (Redis) from App Servers only
- **Outbound:** NONE (completely isolated)

### Bastion Security Group
- **Inbound:** 22 (SSH) from specific IPs only
- **Outbound:** 22 to Private Subnet (for SSH access)

## Network ACLs

Additional layer of defense beyond security groups:

### Public Subnet NACL
- **Inbound:** Allow 80/443 from Cloudflare IPs, 22 from admin IPs
- **Outbound:** Allow established connections

### Private Subnet NACL
- **Inbound:** Allow traffic from public subnet and database subnet
- **Outbound:** Allow traffic to database subnet and internet (for updates)

### Database Subnet NACL
- **Inbound:** Allow 5432/6379 from private subnet only
- **Outbound:** Allow responses to private subnet only

## Prerequisites

1. **Terraform** >= 1.0
   ```bash
   brew install terraform
   # or
   wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
   unzip terraform_1.6.0_linux_amd64.zip
   sudo mv terraform /usr/local/bin/
   ```

2. **Cloud Provider Credentials**

   For Linode:
   ```bash
   export LINODE_TOKEN="your-linode-api-token"
   ```

   For AWS:
   ```bash
   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   export AWS_DEFAULT_REGION="us-east-1"
   ```

3. **SSH Key Pair**
   ```bash
   ssh-keygen -t ed25519 -C "ralph-mode-infrastructure"
   # Save to ~/.ssh/ralph-mode
   ```

## Usage

### Initialize Terraform

```bash
cd infrastructure/terraform
terraform init
```

### Review Plan

```bash
terraform plan
```

### Apply Infrastructure

```bash
# Apply with auto-approval
terraform apply -auto-approve

# Or review first
terraform apply
```

### Destroy Infrastructure

```bash
terraform destroy
```

## Files

- `main.tf` - Main infrastructure configuration
- `vpc.tf` - VPC and subnet definitions
- `security_groups.tf` - Security group rules
- `network_acls.tf` - Network ACL rules
- `compute.tf` - EC2/Linode instances
- `loadbalancer.tf` - Load balancer configuration
- `variables.tf` - Input variables
- `outputs.tf` - Output values
- `terraform.tfvars.example` - Example variables file

## Configuration

1. Copy example variables:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars`:
   ```hcl
   cloudflare_ips = [
     "173.245.48.0/20",
     "103.21.244.0/22",
     # ... more Cloudflare IPs
   ]

   admin_ips = [
     "YOUR.IP.ADDRESS/32"
   ]

   environment = "production"
   region = "us-east"
   ```

3. Apply configuration:
   ```bash
   terraform apply
   ```

## Validation

### Test Network Segmentation

```bash
# From bastion, try to reach database (should work)
ssh bastion "nc -zv database-server 5432"

# From internet, try to reach database (should fail)
nc -zv database-ip 5432

# From app server, try to reach internet (should work via NAT)
ssh app-server "curl -I https://api.groq.com"

# From database, try to reach internet (should fail)
ssh database-server "curl -I https://google.com"  # Should timeout
```

### Verify Security Groups

```bash
# List security groups
terraform state list | grep security_group

# Show security group rules
terraform state show aws_security_group.app_server
```

### Check Network ACLs

```bash
# Show NACL rules
terraform state show aws_network_acl.private_subnet
```

## Monitoring

Terraform outputs important endpoints and IPs:

```bash
terraform output
# Outputs:
# - load_balancer_ip
# - bastion_ip
# - app_server_private_ips
# - database_private_ip
```

## Compliance

This configuration meets:

- **SEC-015** acceptance criteria
- **OWASP** network security best practices
- **CIS** AWS/Linux benchmarks (where applicable)
- **PCI-DSS** network segmentation requirements

## Troubleshooting

### Cannot SSH to instances
- Check bastion security group allows your IP
- Verify SSH key is correct
- Check network ACLs aren't blocking

### Cannot reach database from app
- Verify app server security group has outbound to database
- Verify database security group allows inbound from app
- Check subnet route tables

### No internet from app servers
- Verify NAT gateway is running
- Check route table for private subnet routes to NAT
- Verify NAT security group allows traffic

## Cost Estimate

Based on AWS pricing (approximate):

- VPC: Free
- Subnets: Free
- Security Groups: Free
- Network ACLs: Free
- NAT Gateway: ~$33/month
- Application Servers (t3.medium): ~$30/month each
- Database (t3.small): ~$15/month
- Load Balancer: ~$16/month

**Total:** ~$90-150/month depending on instance count

For Linode:
- VPC (VLAN): Free
- Firewall: Free
- Instances: Starting at $5/month each

**Total:** ~$15-30/month for basic setup

## Maintenance

### Weekly
- Review CloudWatch/monitoring for unusual traffic patterns
- Check security group rules are still appropriate

### Monthly
- Update Cloudflare IP ranges in security groups
  ```bash
  curl https://www.cloudflare.com/ips-v4 -o cloudflare-ips.txt
  terraform apply  # After updating variables
  ```
- Review and rotate credentials

### Quarterly
- Audit security group rules (remove unused)
- Review NACL effectiveness
- Pen-test network segmentation

## References

- [AWS VPC Best Practices](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-best-practices.html)
- [Linode VLANs](https://www.linode.com/docs/products/networking/vlans/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform Linode Provider](https://registry.terraform.io/providers/linode/linode/latest/docs)

---

**Last Updated:** 2026-01-10
**Status:** Implementation Complete ✅
**Security Task:** SEC-015
