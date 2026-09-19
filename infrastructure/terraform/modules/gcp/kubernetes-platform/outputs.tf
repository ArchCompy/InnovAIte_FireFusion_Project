output "cluster_name" {
  description = "GKE cluster name."
  value       = google_container_cluster.this.name
}

output "cluster_location" {
  description = "GKE cluster location."
  value       = google_container_cluster.this.location
}

output "cluster_endpoint" {
  description = "GKE Kubernetes control-plane endpoint."
  value       = google_container_cluster.this.endpoint
  sensitive   = true
}

output "network_name" {
  description = "FireFusion VPC network name."
  value       = google_compute_network.this.name
}

output "subnetwork_name" {
  description = "FireFusion GKE subnetwork name."
  value       = google_compute_subnetwork.gke.name
}

output "node_pool_name" {
  description = "FireFusion GKE node pool name."
  value       = google_container_node_pool.this.name
}