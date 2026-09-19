locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(
    var.tags,
    {
      Platform = "EKS"
    }
  )
}

data "aws_availability_zones" "available" {
  state = "available"
}