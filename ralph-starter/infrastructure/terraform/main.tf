# SEC-015: Network Segmentation - Main Terraform Configuration

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    linode = {
      source  = "linode/linode"
      version = "~> 2.0"
    }
  }

  # Uncomment for remote state storage
  # backend "s3" {
  #   bucket = "ralph-mode-terraform-state"
  #   key    = "network/terraform.tfstate"
  #   region = "us-east-1"
  #   encrypt = true
  #   dynamodb_table = "terraform-lock"
  # }
}

# AWS Provider Configuration
provider "aws" {
  region = var.region

  default_tags {
    tags = var.tags
  }
}

# Linode Provider Configuration
provider "linode" {
  token = var.linode_token != "" ? var.linode_token : null
}

# Data source for latest AMI (AWS)
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# SSH Key Pair
resource "aws_key_pair" "ralph_mode" {
  key_name   = "ralph-mode-${var.environment}"
  public_key = file(var.ssh_public_key_path)

  tags = {
    Name = "ralph-mode-ssh-key"
  }
}
