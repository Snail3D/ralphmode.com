# SEC-015: Security Groups Configuration

# Security Group for Load Balancer (Public Subnet)
resource "aws_security_group" "load_balancer" {
  name        = "ralph-mode-lb-${var.environment}"
  description = "Security group for load balancer - only Cloudflare IPs allowed"
  vpc_id      = aws_vpc.main.id

  # HTTPS from Cloudflare only
  dynamic "ingress" {
    for_each = var.cloudflare_ipv4_ranges
    content {
      description = "HTTPS from Cloudflare"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  # HTTP from Cloudflare only (redirect to HTTPS)
  dynamic "ingress" {
    for_each = var.cloudflare_ipv4_ranges
    content {
      description = "HTTP from Cloudflare"
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  # Outbound to app servers
  egress {
    description     = "To app servers"
    from_port       = var.app_port
    to_port         = var.app_port
    protocol        = "tcp"
    security_groups = [aws_security_group.app_server.id]
  }

  # Outbound for health checks
  egress {
    description     = "Health checks to app servers"
    from_port       = var.app_port
    to_port         = var.app_port
    protocol        = "tcp"
    security_groups = [aws_security_group.app_server.id]
  }

  tags = {
    Name = "ralph-mode-lb-sg-${var.environment}"
    Tier = "public"
  }
}

# Security Group for Application Servers (Private Subnet)
resource "aws_security_group" "app_server" {
  name        = "ralph-mode-app-${var.environment}"
  description = "Security group for application servers"
  vpc_id      = aws_vpc.main.id

  # Inbound from load balancer only
  ingress {
    description     = "App port from load balancer"
    from_port       = var.app_port
    to_port         = var.app_port
    protocol        = "tcp"
    security_groups = [aws_security_group.load_balancer.id]
  }

  # SSH from bastion only
  ingress {
    description     = "SSH from bastion"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }

  # Outbound to database
  egress {
    description     = "PostgreSQL to database"
    from_port       = var.database_port
    to_port         = var.database_port
    protocol        = "tcp"
    security_groups = [aws_security_group.database.id]
  }

  # Outbound to Redis
  egress {
    description     = "Redis to database"
    from_port       = var.redis_port
    to_port         = var.redis_port
    protocol        = "tcp"
    security_groups = [aws_security_group.database.id]
  }

  # Outbound HTTPS for API calls (Groq, Telegram, etc.)
  egress {
    description = "HTTPS to internet (APIs)"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound HTTP for package updates
  egress {
    description = "HTTP to internet (updates)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound DNS
  egress {
    description = "DNS"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "ralph-mode-app-sg-${var.environment}"
    Tier = "private"
  }
}

# Security Group for Database Servers (Isolated Subnet)
resource "aws_security_group" "database" {
  name        = "ralph-mode-db-${var.environment}"
  description = "Security group for database - app servers only"
  vpc_id      = aws_vpc.main.id

  # PostgreSQL from app servers only
  ingress {
    description     = "PostgreSQL from app servers"
    from_port       = var.database_port
    to_port         = var.database_port
    protocol        = "tcp"
    security_groups = [aws_security_group.app_server.id]
  }

  # Redis from app servers only
  ingress {
    description     = "Redis from app servers"
    from_port       = var.redis_port
    to_port         = var.redis_port
    protocol        = "tcp"
    security_groups = [aws_security_group.app_server.id]
  }

  # SSH from bastion only
  ingress {
    description     = "SSH from bastion"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }

  # NO outbound internet access - completely isolated
  # Only allow response traffic to app servers

  egress {
    description     = "Response to app servers"
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.app_server.id]
  }

  tags = {
    Name = "ralph-mode-db-sg-${var.environment}"
    Tier = "database"
  }
}

# Security Group for Bastion Host (Public Subnet)
resource "aws_security_group" "bastion" {
  name        = "ralph-mode-bastion-${var.environment}"
  description = "Security group for bastion host - SSH access"
  vpc_id      = aws_vpc.main.id

  # SSH from admin IPs only
  dynamic "ingress" {
    for_each = var.admin_ips
    content {
      description = "SSH from admin"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  # Outbound SSH to private subnet
  egress {
    description = "SSH to private subnet"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.private_subnet_cidr]
  }

  # Outbound SSH to database subnet
  egress {
    description = "SSH to database subnet"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.database_subnet_cidr]
  }

  # Outbound HTTPS for updates
  egress {
    description = "HTTPS to internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound DNS
  egress {
    description = "DNS"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "ralph-mode-bastion-sg-${var.environment}"
    Tier = "public"
  }
}

# Security Group Rules Summary Output
output "security_group_rules_summary" {
  description = "Summary of security group rules"
  value = {
    load_balancer = {
      id          = aws_security_group.load_balancer.id
      ingress     = "Cloudflare IPs only (80, 443)"
      egress      = "App servers (${var.app_port})"
      description = "Public-facing load balancer"
    }
    app_server = {
      id          = aws_security_group.app_server.id
      ingress     = "Load balancer (${var.app_port}), Bastion (22)"
      egress      = "Database (${var.database_port}, ${var.redis_port}), Internet (443, 80)"
      description = "Application servers in private subnet"
    }
    database = {
      id          = aws_security_group.database.id
      ingress     = "App servers (${var.database_port}, ${var.redis_port}), Bastion (22)"
      egress      = "NONE (completely isolated)"
      description = "Database servers in isolated subnet"
    }
    bastion = {
      id          = aws_security_group.bastion.id
      ingress     = "Admin IPs (22)"
      egress      = "Private subnet (22), Database subnet (22)"
      description = "SSH bastion host"
    }
  }
}
