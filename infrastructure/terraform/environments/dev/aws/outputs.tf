output "cluster_name" {
  description = "Name of the FireFusion EKS cluster."
  value       = module.kubernetes_platform.cluster_name
}

output "cluster_endpoint" {
  description = "EKS Kubernetes API endpoint."
  value       = module.kubernetes_platform.cluster_endpoint
}

output "vpc_id" {
  description = "ID of the FireFusion AWS VPC."
  value       = module.kubernetes_platform.vpc_id
}

output "node_group_name" {
  description = "Name of the managed EKS node group."
  value       = module.kubernetes_platform.node_group_name
}