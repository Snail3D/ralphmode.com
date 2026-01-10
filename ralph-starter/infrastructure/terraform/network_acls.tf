# SEC-015: Network ACLs (Additional Security Layer)

# Network ACL for Public Subnet
resource "aws_network_acl" "public" {
  vpc_id     = aws_vpc.main.id
  subnet_ids = [aws_subnet.public.id]

  tags = {
    Name = "ralph-mode-public-nacl-${var.environment}"
    Tier = "public"
  }
}

# Public Subnet NACL Rules - Inbound
resource "aws_network_acl_rule" "public_inbound_https" {
  count          = length(var.cloudflare_ipv4_ranges)
  network_acl_id = aws_network_acl.public.id
  rule_number    = 100 + count.index
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.cloudflare_ipv4_ranges[count.index]
  from_port      = 443
  to_port        = 443
}

resource "aws_network_acl_rule" "public_inbound_http" {
  count          = length(var.cloudflare_ipv4_ranges)
  network_acl_id = aws_network_acl.public.id
  rule_number    = 200 + count.index
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.cloudflare_ipv4_ranges[count.index]
  from_port      = 80
  to_port        = 80
}

resource "aws_network_acl_rule" "public_inbound_ssh_admin" {
  count          = length(var.admin_ips)
  network_acl_id = aws_network_acl.public.id
  rule_number    = 300 + count.index
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.admin_ips[count.index]
  from_port      = 22
  to_port        = 22
}

# Allow return traffic (ephemeral ports)
resource "aws_network_acl_rule" "public_inbound_ephemeral" {
  network_acl_id = aws_network_acl.public.id
  rule_number    = 400
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 1024
  to_port        = 65535
}

# Public Subnet NACL Rules - Outbound
resource "aws_network_acl_rule" "public_outbound_all" {
  network_acl_id = aws_network_acl.public.id
  rule_number    = 100
  egress         = true
  protocol       = "-1"  # All protocols
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
}

# Network ACL for Private Subnet
resource "aws_network_acl" "private" {
  vpc_id     = aws_vpc.main.id
  subnet_ids = [aws_subnet.private.id]

  tags = {
    Name = "ralph-mode-private-nacl-${var.environment}"
    Tier = "private"
  }
}

# Private Subnet NACL Rules - Inbound
resource "aws_network_acl_rule" "private_inbound_from_public" {
  network_acl_id = aws_network_acl.private.id
  rule_number    = 100
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.public_subnet_cidr
  from_port      = var.app_port
  to_port        = var.app_port
}

resource "aws_network_acl_rule" "private_inbound_ssh_from_public" {
  network_acl_id = aws_network_acl.private.id
  rule_number    = 110
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.public_subnet_cidr
  from_port      = 22
  to_port        = 22
}

resource "aws_network_acl_rule" "private_inbound_from_database" {
  network_acl_id = aws_network_acl.private.id
  rule_number    = 120
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.database_subnet_cidr
  from_port      = 0
  to_port        = 65535
}

# Allow return traffic
resource "aws_network_acl_rule" "private_inbound_ephemeral" {
  network_acl_id = aws_network_acl.private.id
  rule_number    = 400
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 1024
  to_port        = 65535
}

# Private Subnet NACL Rules - Outbound
resource "aws_network_acl_rule" "private_outbound_to_database" {
  network_acl_id = aws_network_acl.private.id
  rule_number    = 100
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.database_subnet_cidr
  from_port      = 0
  to_port        = 65535
}

resource "aws_network_acl_rule" "private_outbound_https" {
  network_acl_id = aws_network_acl.private.id
  rule_number    = 110
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 443
  to_port        = 443
}

resource "aws_network_acl_rule" "private_outbound_http" {
  network_acl_id = aws_network_acl.private.id
  rule_number    = 120
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 80
  to_port        = 80
}

resource "aws_network_acl_rule" "private_outbound_dns" {
  network_acl_id = aws_network_acl.private.id
  rule_number    = 130
  egress         = true
  protocol       = "udp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 53
  to_port        = 53
}

# Allow ephemeral return traffic
resource "aws_network_acl_rule" "private_outbound_ephemeral" {
  network_acl_id = aws_network_acl.private.id
  rule_number    = 400
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 1024
  to_port        = 65535
}

# Network ACL for Database Subnet (Isolated)
resource "aws_network_acl" "database" {
  vpc_id     = aws_vpc.main.id
  subnet_ids = [aws_subnet.database.id]

  tags = {
    Name = "ralph-mode-database-nacl-${var.environment}"
    Tier = "database"
  }
}

# Database Subnet NACL Rules - Inbound
# Only allow traffic from private subnet
resource "aws_network_acl_rule" "database_inbound_postgres_from_private" {
  network_acl_id = aws_network_acl.database.id
  rule_number    = 100
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.private_subnet_cidr
  from_port      = var.database_port
  to_port        = var.database_port
}

resource "aws_network_acl_rule" "database_inbound_redis_from_private" {
  network_acl_id = aws_network_acl.database.id
  rule_number    = 110
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.private_subnet_cidr
  from_port      = var.redis_port
  to_port        = var.redis_port
}

resource "aws_network_acl_rule" "database_inbound_ssh_from_public" {
  network_acl_id = aws_network_acl.database.id
  rule_number    = 120
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.public_subnet_cidr
  from_port      = 22
  to_port        = 22
}

# Database Subnet NACL Rules - Outbound
# Only allow response traffic to private subnet - NO internet access
resource "aws_network_acl_rule" "database_outbound_to_private" {
  network_acl_id = aws_network_acl.database.id
  rule_number    = 100
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.private_subnet_cidr
  from_port      = 1024
  to_port        = 65535
}

# Allow ephemeral responses to bastion
resource "aws_network_acl_rule" "database_outbound_to_public" {
  network_acl_id = aws_network_acl.database.id
  rule_number    = 110
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.public_subnet_cidr
  from_port      = 1024
  to_port        = 65535
}

# Network ACL Summary Output
output "network_acl_summary" {
  description = "Summary of Network ACL configuration"
  value = {
    public = {
      id          = aws_network_acl.public.id
      ingress     = "Cloudflare IPs (80, 443), Admin IPs (22), Ephemeral (1024-65535)"
      egress      = "All traffic allowed"
      description = "Public subnet with limited inbound access"
    }
    private = {
      id          = aws_network_acl.private.id
      ingress     = "Public subnet (${var.app_port}, 22), Database subnet (all), Ephemeral (1024-65535)"
      egress      = "Database subnet (all), Internet (80, 443), DNS (53), Ephemeral (1024-65535)"
      description = "Private subnet with controlled access"
    }
    database = {
      id          = aws_network_acl.database.id
      ingress     = "Private subnet (${var.database_port}, ${var.redis_port}), Public subnet (22)"
      egress      = "Private/Public subnet (ephemeral ports only)"
      description = "Isolated database subnet with NO internet access"
    }
  }
}
