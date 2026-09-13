output "cluster_name" {
  description = "Name of the deployed AKS cluster."
  value       = module.kubernetes_platform.cluster_name
}

output "resource_group_name" {
  description = "Resource group containing the AKS platform."
  value       = module.kubernetes_platform.resource_group_name
}