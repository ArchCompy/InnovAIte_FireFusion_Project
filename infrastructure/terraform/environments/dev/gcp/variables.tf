variable "project_name" {
  description = "Project name used for GCP resource naming."
  type        = string
  default     = "firefusion"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"
}

variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Google Cloud region."
  type        = string
  default     = "australia-southeast1"
}

variable "network_cidr" {
  description = "Primary subnet CIDR for GKE nodes."
  type        = string
  default     = "10.30.0.0/20"
}

variable "pods_cidr" {
  description = "Secondary CIDR range used by Kubernetes pods."
  type        = string
  default     = "10.40.0.0/16"
}

variable "services_cidr" {
  description = "Secondary CIDR range used by Kubernetes services."
  type        = string
  default     = "10.50.0.0/20"
}

variable "node_count" {
  description = "Initial number of GKE worker nodes."
  type        = number
  default     = 1
}

variable "node_min_count" {
  description = "Minimum number of GKE worker nodes."
  type        = number
  default     = 1
}

variable "node_max_count" {
  description = "Maximum number of GKE worker nodes."
  type        = number
  default     = 3
}

variable "node_machine_type" {
  description = "Google Compute Engine machine type used for GKE worker nodes."
  type        = string
  default     = "e2-standard-2"
}

variable "labels" {
  description = "Labels applied to FireFusion GCP resources."
  type        = map(string)

  default = {
    project     = "firefusion"
    environment = "dev"
    managed_by  = "terraform"
    component   = "cloud-infrastructure"
  }
}
variable "master_authorized_network_cidr" {
  description = "Approved CIDR allowed to access the GKE Kubernetes API server."
  type        = string
}
