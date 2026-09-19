locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_labels = merge(
    var.labels,
    {
      platform = "gke"
    }
  )
}