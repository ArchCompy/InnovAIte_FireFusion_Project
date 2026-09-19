variable "project_name" {
  description = "Project name used for AWS resource naming."
  type        = string
  default     = "firefusion"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"
}

variable "region" {
  description = "AWS region used for FireFusion infrastructure."
  type        = string
  default     = "ap-southeast-2"
}

variable "vpc_cidr" {
  description = "CIDR range used by the FireFusion VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "node_count" {
  description = "Desired number of EKS worker nodes."
  type        = number
  default     = 1
}

variable "node_min_count" {
  description = "Minimum number of EKS worker nodes."
  type        = number
  default     = 1
}

variable "node_max_count" {
  description = "Maximum number of EKS worker nodes."
  type        = number
  default     = 3
}

variable "node_instance_type" {
  description = "EC2 instance type used by EKS worker nodes."
  type        = string
  default     = "t3.medium"
}

variable "tags" {
  description = "Common tags applied to FireFusion AWS resources."
  type        = map(string)

  default = {
    Project     = "FireFusion"
    Environment = "dev"
    ManagedBy   = "Terraform"
    Component   = "CloudInfrastructure"
  }
}