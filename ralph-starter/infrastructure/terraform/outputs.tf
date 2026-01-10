# SEC-015: Terraform Outputs

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_id" {
  description = "Public subnet ID"
  value       = aws_subnet.public.id
}

output "private_subnet_id" {
  description = "Private subnet ID"
  value       = aws_subnet.private.id
}

output "database_subnet_id" {
  description = "Database subnet ID"
  value       = aws_subnet.database.id
}

output "nat_gateway_id" {
  description = "NAT Gateway ID"
  value       = var.enable_nat_gateway ? aws_nat_gateway.main[0].id : null
}

output "nat_gateway_public_ip" {
  description = "NAT Gateway public IP"
  value       = var.enable_nat_gateway ? aws_eip.nat[0].public_ip : null
}

output "security_groups" {
  description = "Security group IDs"
  value = {
    load_balancer = aws_security_group.load_balancer.id
    app_server    = aws_security_group.app_server.id
    database      = aws_security_group.database.id
    bastion       = aws_security_group.bastion.id
  }
}

output "network_acls" {
  description = "Network ACL IDs"
  value = {
    public   = aws_network_acl.public.id
    private  = aws_network_acl.private.id
    database = aws_network_acl.database.id
  }
}

output "flow_logs_log_group" {
  description = "CloudWatch log group for VPC flow logs"
  value       = var.enable_flow_logs ? aws_cloudwatch_log_group.flow_logs[0].name : null
}

# Summary output for easy reference
output "network_segmentation_summary" {
  description = "Complete network segmentation summary"
  value = {
    architecture = {
      vpc_cidr         = aws_vpc.main.cidr_block
      public_subnet    = var.public_subnet_cidr
      private_subnet   = var.private_subnet_cidr
      database_subnet  = var.database_subnet_cidr
    }
    security = {
      load_balancer_sg = "Cloudflare IPs only (80, 443)"
      app_server_sg    = "Load balancer (${var.app_port}), Bastion (22)"
      database_sg      = "App servers (${var.database_port}, ${var.redis_port}), NO internet"
      bastion_sg       = "Admin IPs (22)"
    }
    compliance = {
      sec_015_requirement = "Network segmentation with VPC, subnets, security groups, NACLs"
      implemented = "✅ Complete"
      features = [
        "Public subnet for load balancers",
        "Private subnet for application servers",
        "Isolated database subnet (no internet)",
        "Security groups with minimal required ports",
        "No SSH from public internet (bastion only)",
        "Outbound traffic limited to required destinations",
        "Network ACLs as additional layer"
      ]
    }
  }
}

# Connection strings (for configuration)
output "connection_info" {
  description = "Information needed to configure applications"
  value = {
    database_port = var.database_port
    redis_port    = var.redis_port
    app_port      = var.app_port
    environment   = var.environment
  }
  sensitive = false
}
