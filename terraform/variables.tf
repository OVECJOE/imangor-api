variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP zone"
  type        = string
  default     = "us-central1-a"
}

variable "environment" {
  description = "Environment (development, staging, production)"
  type        = string
  default     = "production"
}

variable "api_image" {
  description = "The API container image to deploy"
  type        = string
  default     = "imangor-api:latest"
}

variable "api_min_instances" {
  description = "Minimum number of API instances"
  type        = number
  default     = 1
}

variable "api_max_instances" {
  description = "Maximum number of API instances"
  type        = number
  default     = 10
}

variable "api_memory" {
  description = "Memory allocation for API instances"
  type        = string
  default     = "1Gi"
}

variable "api_cpu" {
  description = "CPU allocation for API instances"
  type        = string
  default     = "1"
}

variable "db_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro"
}

variable "db_disk_size" {
  description = "Cloud SQL disk size in GB"
  type        = number
  default     = 10
}

variable "redis_memory_size_gb" {
  description = "Redis memory size in GB"
  type        = number
  default     = 1
}

variable "domain_name" {
  description = "Domain name for the API"
  type        = string
  default     = "api.imangor.com"
}

variable "allowed_origins" {
  description = "List of allowed CORS origins"
  type        = list(string)
  default     = ["https://imangor.com"]
}

variable "secret_key" {
  description = "Secret key for JWT tokens"
  type        = string
  sensitive   = true
}

variable "database_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "redis_auth_string" {
  description = "Redis auth string"
  type        = string
  sensitive   = true
} 