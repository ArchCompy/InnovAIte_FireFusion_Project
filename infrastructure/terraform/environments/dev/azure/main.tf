module "kubernetes_platform" {
  source = "../../../modules/azure/kubernetes-platform"

  project_name = var.project_name
  environment  = var.environment
  location     = var.location

  node_count     = var.node_count
  node_min_count = var.node_min_count
  node_max_count = var.node_max_count
  node_vm_size   = var.node_vm_size

  tags = var.tags
}