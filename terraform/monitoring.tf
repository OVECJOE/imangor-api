# Cloud Monitoring Workspace
resource "google_monitoring_workspace" "workspace" {
  display_name = "Imangor ${title(var.environment)} Monitoring"
  project      = var.project_id
}

# Cloud Monitoring Dashboard
resource "google_monitoring_dashboard" "api_dashboard" {
  dashboard_json = jsonencode({
    displayName = "Imangor API Dashboard"
    gridLayout = {
      widgets = [
        {
          title = "API Request Rate"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\" resource.label.\"service_name\"=\"${google_cloud_run_v2_service.api.name}\""
                  aggregation = {
                    perSeriesAligner = "ALIGN_RATE"
                  }
                }
              }
              plotType = "LINE"
            }]
            timeshiftDuration = "0s"
            yAxis = {
              label = "requests/sec"
              scale = "LINEAR"
            }
          }
        },
        {
          title = "API Latency"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"run.googleapis.com/request_latencies\" resource.type=\"cloud_run_revision\" resource.label.\"service_name\"=\"${google_cloud_run_v2_service.api.name}\""
                  aggregation = {
                    perSeriesAligner = "ALIGN_PERCENTILE_95"
                  }
                }
              }
              plotType = "LINE"
            }]
            timeshiftDuration = "0s"
            yAxis = {
              label = "latency (ms)"
              scale = "LINEAR"
            }
          }
        },
        {
          title = "API Error Rate"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\" resource.label.\"service_name\"=\"${google_cloud_run_v2_service.api.name}\" metric.label.\"response_code\"=~\"5.*\""
                  aggregation = {
                    perSeriesAligner = "ALIGN_RATE"
                  }
                }
              }
              plotType = "LINE"
            }]
            timeshiftDuration = "0s"
            yAxis = {
              label = "errors/sec"
              scale = "LINEAR"
            }
          }
        },
        {
          title = "Database CPU Usage"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"cloudsql.googleapis.com/database/cpu/utilization\" resource.type=\"cloudsql_database\" resource.label.\"database_id\"=\"${google_sql_database_instance.postgres.connection_name}\""
                }
              }
              plotType = "LINE"
            }]
            timeshiftDuration = "0s"
            yAxis = {
              label = "CPU %"
              scale = "LINEAR"
            }
          }
        },
        {
          title = "Redis Memory Usage"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"redis.googleapis.com/memory/usage_ratio\" resource.type=\"redis_instance\" resource.label.\"instance_id\"=\"${google_redis_instance.redis.name}\""
                }
              }
              plotType = "LINE"
            }]
            timeshiftDuration = "0s"
            yAxis = {
              label = "memory usage %"
              scale = "LINEAR"
            }
          }
        }
      ]
    }
  })
  project = var.project_id
}

# Alert Policies
resource "google_monitoring_alert_policy" "api_high_error_rate" {
  display_name = "High API Error Rate"
  combiner     = "OR"
  conditions {
    display_name = "Error rate is high"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\" resource.label.\"service_name\"=\"${google_cloud_run_v2_service.api.name}\" metric.label.\"response_code\"=~\"5.*\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
}

resource "google_monitoring_alert_policy" "api_high_latency" {
  display_name = "High API Latency"
  combiner     = "OR"
  conditions {
    display_name = "Latency is high"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_latencies\" resource.type=\"cloud_run_revision\" resource.label.\"service_name\"=\"${google_cloud_run_v2_service.api.name}\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 1000
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_PERCENTILE_95"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
}

resource "google_monitoring_alert_policy" "db_high_cpu" {
  display_name = "High Database CPU Usage"
  combiner     = "OR"
  conditions {
    display_name = "CPU usage is high"
    condition_threshold {
      filter          = "metric.type=\"cloudsql.googleapis.com/database/cpu/utilization\" resource.type=\"cloudsql_database\" resource.label.\"database_id\"=\"${google_sql_database_instance.postgres.connection_name}\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
}

# Notification Channel
resource "google_monitoring_notification_channel" "email" {
  display_name = "Email Alerts"
  type         = "email"
  labels = {
    email_address = "alerts@imangor.com"
  }
}

# Log-based Metrics
resource "google_logging_metric" "api_errors" {
  name   = "api_errors"
  filter = "resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${google_cloud_run_v2_service.api.name}\" severity>=ERROR"
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    labels {
      key         = "error_type"
      value_type  = "STRING"
      description = "Type of error"
    }
  }
  label_extractors = {
    "error_type" = "EXTRACT(jsonPayload.error.type)"
  }
}

# Log Sink
resource "google_logging_project_sink" "api_logs" {
  name                   = "api-logs-${var.environment}"
  destination            = "bigquery.googleapis.com/projects/${var.project_id}/datasets/api_logs"
  filter                 = "resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${google_cloud_run_v2_service.api.name}\""
  unique_writer_identity = true
}

# BigQuery Dataset for Logs
resource "google_bigquery_dataset" "api_logs" {
  dataset_id  = "api_logs"
  description = "API logs dataset"
  location    = var.region
  delete_protection = var.environment == "production" ? true : false
}

# IAM for Log Sink
resource "google_project_iam_member" "log_writer" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = google_logging_project_sink.api_logs.writer_identity
} 