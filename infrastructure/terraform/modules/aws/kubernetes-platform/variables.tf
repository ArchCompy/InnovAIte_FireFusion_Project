variable "project_name" {
  description = "Project name used for AWS resource naming."
  type        = string
}

variable "environment" {
  description = "Deployment environment."
  type        = string
}

variable "region" {
  description = "AWS region used for FireFusion infrastructure."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR range used by the FireFusion VPC."
  type        = string
}

variable "node_count" {
  description = "Desired number of EKS worker nodes."
  type        = number
}

variable "node_min_count" {
  description = "Minimum number of EKS worker nodes."
  type        = number
}

variable "node_max_count" {
  description = "Maximum number of EKS worker nodes."
  type        = number
}

variable "node_instance_type" {
  description = "EC2 instance type used by EKS worker nodes."
  type        = string
}

variable "tags" {
  description = "Common tags applied to AWS resources."
  type        = map(string)
}