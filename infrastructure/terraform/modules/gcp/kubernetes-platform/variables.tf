variable "project_name" {
  description = "Project name used for Google Cloud resource naming."
  type        = string
}

variable "environment" {
  description = "Deployment environment."
  type        = string
}

variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Google Cloud region."
  type        = string
}

variable "network_cidr" {
  description = "Primary GKE node subnet CIDR."
  type        = string
}

variable "pods_cidr" {
  description = "Secondary pod IP range."
  type        = string
}

variable "services_cidr" {
  description = "Secondary service IP range."
  type        = string
}

variable "node_count" {
  description = "Initial GKE node count."
  type        = number
}

variable "node_min_count" {
  description = "Minimum GKE node count."
  type        = number
}

variable "node_max_count" {
  description = "Maximum GKE node count."
  type        = number
}

variable "node_machine_type" {
  description = "Compute Engine machine type used by GKE worker nodes."
  type        = string
}

variable "labels" {
  description = "Common Google Cloud labels."
  type        = map(string)
}
variable "master_authorized_network_cidr" {
  description = "Approved CIDR allowed to access the GKE Kubernetes API server."
  type        = string
}
