resource "google_container_cluster" "this" {
  project  = var.project_id
  name     = "gke-${local.name_prefix}"
  location = var.region

  network    = google_compute_network.this.id
  subnetwork = google_compute_subnetwork.gke.id

  remove_default_node_pool = true

  initial_node_count = 1

  networking_mode = "VPC_NATIVE"

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Restrict Kubernetes API access to an explicitly approved network.
  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = var.master_authorized_network_cidr
      display_name = "approved-management-network"
    }
  }

  release_channel {
    channel = "REGULAR"
  }

  deletion_protection = false

  resource_labels = local.common_labels
}

resource "google_container_node_pool" "this" {
  project = var.project_id

  name = "${local.name_prefix}-nodes"

  location = var.region
  cluster  = google_container_cluster.this.name

  initial_node_count = var.node_count

  autoscaling {
    min_node_count = var.node_min_count
    max_node_count = var.node_max_count
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  node_config {
    machine_type = var.node_machine_type

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    labels = local.common_labels

    metadata = {
      disable-legacy-endpoints = "true"
    }

    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
}