resource "aws_eks_cluster" "this" {
  name = "eks-${local.name_prefix}"

  role_arn = aws_iam_role.eks_cluster.arn

  encryption_config {
    resources = ["secrets"]

    provider {
      key_arn = aws_kms_key.eks.arn
    }
  }

  # Use private subnets and disable the public Kubernetes API endpoint.
  vpc_config {
    subnet_ids = [
      aws_subnet.private_a.id,
      aws_subnet.private_b.id
    ]

    endpoint_private_access = true
    endpoint_public_access  = false
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy
  ]

  tags = local.common_tags
}

resource "aws_eks_node_group" "this" {
  cluster_name = aws_eks_cluster.this.name

  node_group_name = "${local.name_prefix}-nodes"

  node_role_arn = aws_iam_role.eks_nodes.arn

  # Worker nodes remain private and use NAT for required outbound access.
  subnet_ids = [
    aws_subnet.private_a.id,
    aws_subnet.private_b.id
  ]

  instance_types = [
    var.node_instance_type
  ]

  capacity_type = "ON_DEMAND"

  scaling_config {
    desired_size = var.node_count
    min_size     = var.node_min_count
    max_size     = var.node_max_count
  }

  update_config {
    max_unavailable = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy
  ]

  tags = local.common_tags
}
