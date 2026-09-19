module "kubernetes_platform" {
  source = "../../../modules/gcp/kubernetes-platform"

  project_name = var.project_name
  environment  = var.environment

  project_id = var.project_id
  region     = var.region

  network_cidr  = var.network_cidr
  pods_cidr     = var.pods_cidr
  services_cidr = var.services_cidr

  master_authorized_network_cidr = var.master_authorized_network_cidr

  node_count        = var.node_count
  node_min_count    = var.node_min_count
  node_max_count    = var.node_max_count
  node_machine_type = var.node_machine_type

  labels = var.labels
}