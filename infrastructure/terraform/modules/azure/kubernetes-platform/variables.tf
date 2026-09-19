variable "project_name" {
  description = "Project name used for Azure resource naming."
  type        = string
}

variable "environment" {
  description = "Deployment environment."
  type        = string
}

variable "location" {
  description = "Azure deployment region."
  type        = string
}

variable "node_count" {
  description = "Initial AKS node count."
  type        = number
}

variable "node_min_count" {
  description = "Minimum AKS node count."
  type        = number
}

variable "node_max_count" {
  description = "Maximum AKS node count."
  type        = number
}

variable "node_vm_size" {
  description = "AKS worker node VM size."
  type        = string
}

variable "tags" {
  description = "Common Azure resource tags."
  type        = map(string)
}