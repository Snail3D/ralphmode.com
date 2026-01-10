# SEC-015: Network Segmentation - Terraform Variables

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
  default     = "production"
}

variable "region" {
  description = "Cloud provider region"
  type        = string
  default     = "us-east-1"  # AWS
  # default = "us-east"      # Linode
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for public subnet (load balancers)"
  type        = string
  default     = "10.0.1.0/24"
}

variable "private_subnet_cidr" {
  description = "CIDR block for private subnet (application servers)"
  type        = string
  default     = "10.0.2.0/24"
}

variable "database_subnet_cidr" {
  description = "CIDR block for database subnet (isolated)"
  type        = string
  default     = "10.0.3.0/24"
}

variable "cloudflare_ipv4_ranges" {
  description = "Cloudflare IPv4 ranges (update monthly from https://www.cloudflare.com/ips-v4)"
  type        = list(string)
  default = [
    "173.245.48.0/20",
    "103.21.244.0/22",
    "103.22.200.0/22",
    "103.31.4.0/22",
    "141.101.64.0/18",
    "108.162.192.0/18",
    "190.93.240.0/20",
    "188.114.96.0/20",
    "197.234.240.0/22",
    "198.41.128.0/17",
    "162.158.0.0/15",
    "104.16.0.0/13",
    "104.24.0.0/14",
    "172.64.0.0/13",
    "131.0.72.0/22"
  ]
}

variable "cloudflare_ipv6_ranges" {
  description = "Cloudflare IPv6 ranges"
  type        = list(string)
  default = [
    "2400:cb00::/32",
    "2606:4700::/32",
    "2803:f800::/32",
    "2405:b500::/32",
    "2405:8100::/32",
    "2a06:98c0::/29",
    "2c0f:f248::/32"
  ]
}

variable "admin_ips" {
  description = "IP addresses allowed to SSH to bastion host (CHANGE THIS)"
  type        = list(string)
  default = [
    "0.0.0.0/0"  # INSECURE: Replace with your actual IP address
  ]
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key for instance access"
  type        = string
  default     = "~/.ssh/ralph-mode.pub"
}

variable "app_server_count" {
  description = "Number of application servers to deploy"
  type        = number
  default     = 2
}

variable "instance_type_app" {
  description = "Instance type for application servers"
  type        = string
  default     = "t3.medium"  # AWS
  # default = "g6-standard-2"  # Linode (4GB RAM)
}

variable "instance_type_db" {
  description = "Instance type for database server"
  type        = string
  default     = "t3.small"  # AWS
  # default = "g6-standard-1"  # Linode (2GB RAM)
}

variable "instance_type_bastion" {
  description = "Instance type for bastion host"
  type        = string
  default     = "t3.micro"  # AWS
  # default = "g6-nanode-1"   # Linode (1GB RAM)
}

variable "enable_nat_gateway" {
  description = "Enable NAT gateway for private subnet internet access"
  type        = bool
  default     = true
}

variable "enable_monitoring" {
  description = "Enable CloudWatch/monitoring"
  type        = bool
  default     = true
}

variable "enable_flow_logs" {
  description = "Enable VPC flow logs for security monitoring"
  type        = bool
  default     = true
}

variable "database_port" {
  description = "Database port (PostgreSQL default: 5432, MySQL: 3306)"
  type        = number
  default     = 5432
}

variable "redis_port" {
  description = "Redis cache port"
  type        = number
  default     = 6379
}

variable "app_port" {
  description = "Application server port"
  type        = number
  default     = 8080
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "Ralph Mode"
    ManagedBy   = "Terraform"
    SecurityReq = "SEC-015"
    Environment = "production"
  }
}

# Linode-specific variables
variable "linode_token" {
  description = "Linode API token (set via LINODE_TOKEN env var)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "linode_region" {
  description = "Linode region"
  type        = string
  default     = "us-east"
}

# AWS-specific variables
variable "aws_availability_zones" {
  description = "AWS availability zones for high availability"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}
