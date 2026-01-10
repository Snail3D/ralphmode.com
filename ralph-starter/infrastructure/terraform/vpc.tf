# SEC-015: VPC and Subnet Configuration

# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "ralph-mode-vpc-${var.environment}"
  }
}

# Internet Gateway (for public subnet)
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "ralph-mode-igw-${var.environment}"
  }
}

# Public Subnet (Load Balancers, NAT, Bastion)
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = var.aws_availability_zones[0]
  map_public_ip_on_launch = true

  tags = {
    Name = "ralph-mode-public-subnet-${var.environment}"
    Tier = "public"
  }
}

# Private Subnet (Application Servers)
resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidr
  availability_zone = var.aws_availability_zones[0]

  tags = {
    Name = "ralph-mode-private-subnet-${var.environment}"
    Tier = "private"
  }
}

# Database Subnet (Isolated)
resource "aws_subnet" "database" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.database_subnet_cidr
  availability_zone = var.aws_availability_zones[0]

  tags = {
    Name = "ralph-mode-database-subnet-${var.environment}"
    Tier = "database"
  }
}

# Elastic IP for NAT Gateway
resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? 1 : 0
  domain = "vpc"

  tags = {
    Name = "ralph-mode-nat-eip-${var.environment}"
  }

  depends_on = [aws_internet_gateway.main]
}

# NAT Gateway (allows private subnet to access internet for updates)
resource "aws_nat_gateway" "main" {
  count         = var.enable_nat_gateway ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public.id

  tags = {
    Name = "ralph-mode-nat-${var.environment}"
  }

  depends_on = [aws_internet_gateway.main]
}

# Route Table for Public Subnet
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "ralph-mode-public-rt-${var.environment}"
  }
}

# Route Table for Private Subnet (with NAT)
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  dynamic "route" {
    for_each = var.enable_nat_gateway ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.main[0].id
    }
  }

  tags = {
    Name = "ralph-mode-private-rt-${var.environment}"
  }
}

# Route Table for Database Subnet (NO internet access)
resource "aws_route_table" "database" {
  vpc_id = aws_vpc.main.id

  # No routes to internet gateway or NAT - completely isolated

  tags = {
    Name = "ralph-mode-database-rt-${var.environment}"
  }
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "database" {
  subnet_id      = aws_subnet.database.id
  route_table_id = aws_route_table.database.id
}

# VPC Flow Logs (for security monitoring)
resource "aws_flow_log" "main" {
  count                = var.enable_flow_logs ? 1 : 0
  iam_role_arn         = aws_iam_role.flow_logs[0].arn
  log_destination      = aws_cloudwatch_log_group.flow_logs[0].arn
  traffic_type         = "ALL"
  vpc_id               = aws_vpc.main.id
  log_destination_type = "cloud-watch-logs"

  tags = {
    Name = "ralph-mode-flow-logs-${var.environment}"
  }
}

# CloudWatch Log Group for Flow Logs
resource "aws_cloudwatch_log_group" "flow_logs" {
  count             = var.enable_flow_logs ? 1 : 0
  name              = "/aws/vpc/ralph-mode-${var.environment}"
  retention_in_days = 30

  tags = {
    Name = "ralph-mode-flow-logs"
  }
}

# IAM Role for Flow Logs
resource "aws_iam_role" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0
  name  = "ralph-mode-flow-logs-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Flow Logs
resource "aws_iam_role_policy" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0
  name  = "ralph-mode-flow-logs-policy"
  role  = aws_iam_role.flow_logs[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}
