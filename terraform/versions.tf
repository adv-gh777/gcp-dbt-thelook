terraform {
  required_version = ">= 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.location

  # The Billing Budgets API rejects user ADC unless a quota project is sent.
  user_project_override = true
  billing_project       = var.project_id
}
