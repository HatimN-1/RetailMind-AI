# OPTIONAL reference infrastructure; NOT applied or billed in this delivery.
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" }
  }
}
provider "azurerm" { features {} }
variable "project_prefix" { type = string; default = "retailmind" }
variable "location" { type = string; default = "francecentral" }
variable "storage_account_name" {
  type = string
  description = "Globally unique lowercase storage account name, 3-24 characters"
}
resource "azurerm_resource_group" "demo" {
  name = "${var.project_prefix}-rg"
  location = var.location
}
resource "azurerm_storage_account" "demo" {
  name = var.storage_account_name
  resource_group_name = azurerm_resource_group.demo.name
  location = azurerm_resource_group.demo.location
  account_tier = "Standard"
  account_replication_type = "LRS"
  min_tls_version = "TLS1_2"
  allow_nested_items_to_be_public = false
}
output "storage_account_id" { value = azurerm_storage_account.demo.id }
