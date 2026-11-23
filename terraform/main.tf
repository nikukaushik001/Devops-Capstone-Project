terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  default = "us-east-1"
}

# Production VPC
resource "aws_vpc" "fintech_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "fintech-prod-vpc"
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}

# Multi-AZ Subnets
resource "aws_subnet" "public_1" {
  vpc_id            = aws_vpc.fintech_vpc.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"
}

resource "aws_subnet" "public_2" {
  vpc_id            = aws_vpc.fintech_vpc.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "us-east-1b"
}

# AWS EKS Cluster
resource "aws_eks_cluster" "prod_cluster" {
  name     = "fintech-core-prod-eks"
  role_arn = "arn:aws:iam::123456789012:role/eks-cluster-role"
  version  = "1.30"

  vpc_config {
    subnet_ids = [aws_subnet.public_1.id, aws_subnet.public_2.id]
  }

  tags = {
    Environment = "production"
    Compliance  = "PCI-DSS-Level-1"
  }
}

