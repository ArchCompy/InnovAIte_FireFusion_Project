module "kubernetes_platform" {
  source = "../../../modules/aws/kubernetes-platform"

  project_name = var.project_name
  environment  = var.environment
  region       = var.region

  vpc_cidr = var.vpc_cidr

  node_count         = var.node_count
  node_min_count     = var.node_min_count
  node_max_count     = var.node_max_count
  node_instance_type = var.node_instance_type

  tags = var.tags
}