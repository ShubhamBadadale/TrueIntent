terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
    }
  }
}

provider "google" {
  project = "example-project"
  region = "us-central1"
}

resource "google_compute_network" "main" {
  name = "main"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "public" {
  name = "public"
  ip_cidr_range = "10.0.1.0/24"
  region = "us-central1"
  network = google_compute_network.main.id
}

resource "google_compute_firewall" "web_fw" {
  name = "web_fw"
  network = google_compute_network.main.name
  allow {
    protocol = "tcp"
    ports = [80]
  }
  allow {
    protocol = "tcp"
    ports = [443]
  }
  source_ranges = ["0.0.0.0/0", "0.0.0.0/0"]
}

resource "google_compute_instance" "web" {
  name = "web"
  machine_type = "e2-micro"
  zone = "us-central1-a"
  boot_disk { initialize_params { image = "ubuntu-22.04" } }
  network_interface { subnetwork = google_compute_subnetwork.public.id }
}
