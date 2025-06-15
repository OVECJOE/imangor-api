terraform {
  required_version = ">= 1.0.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "imangor-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "storage.googleapis.com",
    "compute.googleapis.com"
  ])
  
  project = var.project_id
  service = each.key

  disable_dependent_services = false
  disable_on_destroy        = false
}

# Create service account for Cloud Run
resource "google_service_account" "cloud_run_sa" {
  account_id   = "imangor-api-sa"
  display_name = "Imangor API Service Account"
  description  = "Service account for Imangor API Cloud Run service"
}

# Grant necessary roles to the service account
resource "google_project_iam_member" "cloud_run_sa_roles" {
  for_each = toset([
    "roles/run.invoker",
    "roles/secretmanager.secretAccessor",
    "roles/storage.objectViewer",
    "roles/cloudsql.client",
    "roles/redis.viewer"
  ])
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Create Artifact Registry repository
resource "google_artifact_registry_repository" "api_repo" {
  location      = var.region
  repository_id = "imangor-api"
  description   = "Docker repository for Imangor API"
  format        = "DOCKER"
}

# Create Cloud Storage bucket for application files
resource "google_storage_bucket" "app_storage" {
  name          = "imangor-storage"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true
  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

# Create VPC connector for Cloud Run
resource "google_vpc_access_connector" "connector" {
  name          = "imangor-connector"
  ip_cidr_range = "10.8.0.0/28"
  network       = "default"
  region        = var.region
} 