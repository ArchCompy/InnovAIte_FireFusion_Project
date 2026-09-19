output "cluster_name" {
  description = "EKS cluster name."
  value       = aws_eks_cluster.this.name
}

output "cluster_endpoint" {
  description = "EKS cluster API endpoint."
  value       = aws_eks_cluster.this.endpoint
}

output "cluster_certificate_authority" {
  description = "EKS cluster certificate authority data."
  value       = aws_eks_cluster.this.certificate_authority[0].data
  sensitive   = true
}

output "node_group_name" {
  description = "EKS managed node group name."
  value       = aws_eks_node_group.this.node_group_name
}

output "vpc_id" {
  description = "FireFusion VPC ID."
  value       = aws_vpc.this.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs used by the EKS environment."

  value = [
    aws_subnet.public_a.id,
    aws_subnet.public_b.id
  ]
}