# Cloud SQL Instance
resource "google_sql_database_instance" "postgres" {
  name             = "imangor-${var.environment}-db"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = var.db_tier
    disk_size         = var.db_disk_size
    disk_type         = "PD_SSD"
    availability_type = "REGIONAL"

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "02:00"
    }

    ip_configuration {
      ipv4_enabled = true
      require_ssl  = true
    }

    insights_config {
      query_insights_enabled = true
      query_string_length    = 1024
      record_application_tags = true
      record_client_address  = true
    }
  }

  deletion_protection = var.environment == "production" ? true : false
}

resource "google_sql_database" "database" {
  name     = "imangor"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "user" {
  name     = "imangor"
  instance = google_sql_database_instance.postgres.name
  password = var.database_password
}

# Redis Instance
resource "google_redis_instance" "redis" {
  name           = "imangor-${var.environment}-redis"
  memory_size_gb = var.redis_memory_size_gb
  region         = var.region
  redis_version  = "REDIS_7_0"

  authorized_network = google_compute_network.vpc.id

  auth_enabled = true
  auth_string  = var.redis_auth_string

  persistence_config {
    persistence_mode = "RDB"
    rdb_snapshot_period = "TWELVE_HOURS"
  }
}

# Cloud Run Service
resource "google_cloud_run_v2_service" "api" {
  name     = "imangor-${var.environment}-api"
  location = var.region

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/imangor-api/${var.api_image}"

      resources {
        limits = {
          cpu    = var.api_cpu
          memory = var.api_memory
        }
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "DATABASE_URL"
        value = "postgresql://${google_sql_user.user.name}:${var.database_password}@${google_sql_database_instance.postgres.private_ip_address}/${google_sql_database.database.name}"
      }

      env {
        name  = "REDIS_URL"
        value = "redis://:${var.redis_auth_string}@${google_redis_instance.redis.host}:${google_redis_instance.redis.port}"
      }

      env {
        name  = "SECRET_KEY"
        value = var.secret_key
      }

      env {
        name  = "ALLOWED_ORIGINS"
        value = join(",", var.allowed_origins)
      }

      startup_probe {
        initial_delay_seconds = 0
        timeout_seconds       = 1
        period_seconds        = 3
        failure_threshold     = 1
        tcp_socket {
          port = 8000
        }
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8000
        }
      }
    }

    scaling {
      min_instance_count = var.api_min_instances
      max_instance_count = var.api_max_instances
    }

    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "ALL_TRAFFIC"
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# IAM policy for Cloud Run
resource "google_cloud_run_service_iam_member" "public" {
  location = google_cloud_run_v2_service.api.location
  service  = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Custom Domain Mapping
resource "google_cloud_run_domain_mapping" "domain" {
  location = var.region
  name     = var.domain_name

  metadata {
    namespace = var.project_id
  }

  spec {
    route_name = google_cloud_run_v2_service.api.name
  }
}

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "imangor-${var.environment}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "imangor-${var.environment}-subnet"
  ip_cidr_range = "10.0.0.0/28"
  network       = google_compute_network.vpc.id
  region        = var.region
}

# VPC Connector
resource "google_vpc_access_connector" "connector" {
  name          = "imangor-${var.environment}-connector"
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.vpc.name
  region        = var.region
} 