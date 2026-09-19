resource "azurerm_kubernetes_cluster" "this" {

  name                = "aks-${local.name_prefix}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name

  dns_prefix = local.name_prefix

  identity {
    type = "SystemAssigned"
  }

  # Enable OIDC and Azure Workload Identity so workloads can
  # authenticate to Azure services without long-lived credentials.
  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  # Restrict the Kubernetes API to private network access.
  private_cluster_enabled = true

  # Explicitly enable Kubernetes RBAC.
  role_based_access_control_enabled = true

  default_node_pool {
    name                 = "system"
    vm_size              = var.node_vm_size
    auto_scaling_enabled = true

    min_count = var.node_min_count
    max_count = var.node_max_count

    vnet_subnet_id = azurerm_subnet.aks.id
  }

  network_profile {
    network_plugin = "azure"
    network_policy = "azure"
  }

  tags = var.tags
}
