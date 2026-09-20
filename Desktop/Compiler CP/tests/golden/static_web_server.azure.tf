terraform {
  required_providers {
    azurerm = {
      source = "hashicorp/azurerm"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "main" {
  name = "mcdc-rg"
  location = "East US"
}

resource "azurerm_virtual_network" "main" {
  name = "main"
  address_space = ["10.0.0.0/16"]
  location = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_subnet" "public" {
  name = "public"
  resource_group_name = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes = ["10.0.1.0/24"]
}

resource "azurerm_network_security_group" "web_fw" {
  name = "web_fw"
  location = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_network_security_rule" "web_fw_80" {
  name = "web_fw-80"
  priority = 100
  direction = "Inbound"
  access = "Allow"
  protocol = "Tcp"
  source_port_range = "*"
  destination_port_range = "80"
  source_address_prefix = "0.0.0.0/0"
  destination_address_prefix = "*"
  resource_group_name = azurerm_resource_group.main.name
  network_security_group_name = azurerm_network_security_group.web_fw.name
}

resource "azurerm_network_security_rule" "web_fw_443" {
  name = "web_fw-443"
  priority = 101
  direction = "Inbound"
  access = "Allow"
  protocol = "Tcp"
  source_port_range = "*"
  destination_port_range = "443"
  source_address_prefix = "0.0.0.0/0"
  destination_address_prefix = "*"
  resource_group_name = azurerm_resource_group.main.name
  network_security_group_name = azurerm_network_security_group.web_fw.name
}

resource "azurerm_network_interface" "web" {
  name = "web-nic"
  location = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  ip_configuration {
    name = "internal"
    subnet_id = azurerm_subnet.public.id
    private_ip_address_allocation = "Dynamic"
  }
}

resource "azurerm_linux_virtual_machine" "web" {
  name = "web"
  resource_group_name = azurerm_resource_group.main.name
  location = azurerm_resource_group.main.location
  size = "Standard_B1s"
  admin_username = "adminuser"
  network_interface_ids = [azurerm_network_interface.web.id]
  admin_ssh_key { username = "adminuser" public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDexample" }
  os_disk { caching = "ReadWrite" storage_account_type = "Standard_LRS" }
  source_image_reference { publisher = "Canonical" offer = "0001-com-ubuntu-server-jammy" sku = "22_04-lts" version = "latest" }
}
