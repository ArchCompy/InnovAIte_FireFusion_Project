output "cluster_name" {
  description = "Name of the FireFusion GKE cluster."
  value       = module.kubernetes_platform.cluster_name
}

output "cluster_location" {
  description = "GKE cluster region."
  value       = module.kubernetes_platform.cluster_location
}

output "cluster_endpoint" {
  description = "GKE control-plane endpoint."
  value       = module.kubernetes_platform.cluster_endpoint
  sensitive   = true
}

output "network_name" {
  description = "FireFusion VPC network name."
  value       = module.kubernetes_platform.network_name
}

output "subnetwork_name" {
  description = "FireFusion GKE subnetwork name."
  value       = module.kubernetes_platform.subnetwork_name
}