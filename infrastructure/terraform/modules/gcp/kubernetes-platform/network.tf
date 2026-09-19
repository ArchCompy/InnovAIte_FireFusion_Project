resource "google_compute_network" "this" {
  project = var.project_id

  name = "vpc-${local.name_prefix}"

  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "gke" {
  project = var.project_id

  name   = "snet-${local.name_prefix}-gke"
  region = var.region

  network = google_compute_network.this.id

  ip_cidr_range = var.network_cidr

  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.pods_cidr
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.services_cidr
  }
}