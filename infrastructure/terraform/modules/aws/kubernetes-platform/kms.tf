resource "aws_kms_key" "eks" {
  description             = "KMS key for EKS Kubernetes secret encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(
    local.common_tags,
    {
      Name = "kms-${local.name_prefix}-eks"
    }
  )
}

resource "aws_kms_alias" "eks" {
  name          = "alias/${local.name_prefix}-eks"
  target_key_id = aws_kms_key.eks.key_id
}
