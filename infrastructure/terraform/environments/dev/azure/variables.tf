variable "project_name" {
  description = "Project name used for resource naming."
  type        = string
  default     = "firefusion"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region."
  type        = string
  default     = "australiaeast"
}

variable "node_count" {
  description = "Initial AKS node count."
  type        = number
  default     = 1
}

variable "node_min_count" {
  description = "Minimum number of worker nodes."
  type        = number
  default     = 1
}

variable "node_max_count" {
  description = "Maximum number of worker nodes."
  type        = number
  default     = 3
}

variable "node_vm_size" {
  description = "AKS worker node VM size."
  type        = string
  default     = "Standard_B2s"
}

variable "tags" {
  description = "Common resource tags."
  type        = map(string)

  default = {
    Project   = "FireFusion"
    ManagedBy = "Terraform"
    Purpose   = "Capstone"
  }
}