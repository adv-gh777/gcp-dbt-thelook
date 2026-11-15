data "google_project" "this" {
  project_id = var.project_id
}

# --- APIs -------------------------------------------------------------------

locals {
  services = [
    "bigquery.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com", # service account impersonation
    "billingbudgets.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ]

  # Medallion layers: raw (views over public source), core (conformed), mart (star schema)
  datasets = {
    raw  = "Bronze: thin typed views over bigquery-public-data.thelook_ecommerce"
    core = "Silver: cleaned, conformed models"
    mart = "Gold: star schema for BI (contracted)"
  }
}

resource "google_project_service" "apis" {
  for_each           = toset(local.services)
  service            = each.value
  disable_on_destroy = false
}

# --- BigQuery datasets ------------------------------------------------------

resource "google_bigquery_dataset" "layer" {
  for_each      = local.datasets
  dataset_id    = each.key
  description   = each.value
  location      = var.location
  friendly_name = each.key

  # Lets `terraform destroy` clean up tables dbt created.
  delete_contents_on_destroy = true

  labels = { project = "thelook-dbt", layer = each.key }

  depends_on = [google_project_service.apis]
}

# --- dbt service account (least privilege) ----------------------------------

resource "google_service_account" "dbt" {
  account_id   = "dbt-runner"
  display_name = "dbt runner"
  description  = "Runs dbt; can query BigQuery and write only to raw/core/mart."
  depends_on   = [google_project_service.apis]
}

# Running query jobs is a project-level permission; it cannot be scoped to a dataset.
resource "google_project_iam_member" "dbt_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = google_service_account.dbt.member
}

# Write access only on the three project datasets.
resource "google_bigquery_dataset_iam_member" "dbt_editor" {
  for_each   = google_bigquery_dataset.layer
  dataset_id = each.value.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_service_account.dbt.member
}

# Keyless auth: you impersonate the SA via your own ADC instead of downloading a key.
resource "google_service_account_iam_member" "developer_impersonation" {
  service_account_id = google_service_account.dbt.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "user:${var.developer_email}"
}

# --- Budget alert -----------------------------------------------------------
# Notification only (emails billing admins at 50/90/100%); it does NOT cap spend.
# The hard guardrail is `maximum_bytes_billed` in dbt/profiles.yml.

resource "google_billing_budget" "project" {
  billing_account = var.billing_account_id
  display_name    = "${var.project_id} monthly budget"

  budget_filter {
    projects = ["projects/${data.google_project.this.number}"]
  }

  amount {
    specified_amount {
      # currency_code omitted: defaults to (and must match) the billing account currency.
      units = tostring(var.budget_amount)
    }
  }

  threshold_rules { threshold_percent = 0.5 }
  threshold_rules { threshold_percent = 0.9 }
  threshold_rules { threshold_percent = 1.0 }

  depends_on = [google_project_service.apis]
}

# --- Analytics agent: read-only access to the mart layer only ----------------

resource "google_service_account" "mart_reader" {
  account_id   = "mart-reader"
  display_name = "mart reader (AI agent)"
  description  = "Used by the analytics agent via MCP Toolbox; read-only on the mart dataset."
  depends_on   = [google_project_service.apis]
}

# Needed to run query jobs at all (project-level, cannot be dataset-scoped).
resource "google_project_iam_member" "mart_reader_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = google_service_account.mart_reader.member
}

# Read access to the mart dataset only (no raw/core).
resource "google_bigquery_dataset_iam_member" "mart_reader_viewer" {
  dataset_id = google_bigquery_dataset.layer["mart"].dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = google_service_account.mart_reader.member
}

resource "google_service_account_iam_member" "developer_impersonates_mart_reader" {
  service_account_id = google_service_account.mart_reader.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "user:${var.developer_email}"
}
