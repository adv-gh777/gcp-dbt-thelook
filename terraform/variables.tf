variable "project_id" {
  description = "Existing GCP project ID (with billing linked)."
  type        = string
}

variable "billing_account_id" {
  description = "Billing account ID (XXXXXX-XXXXXX-XXXXXX) used for the budget alert."
  type        = string
}

variable "developer_email" {
  description = "Your Google account; granted permission to impersonate the dbt service account."
  type        = string
}

variable "location" {
  description = "BigQuery location. Must match the public dataset (US multi-region)."
  type        = string
  default     = "US"
}

variable "budget_amount" {
  description = "Monthly budget in the billing account's currency."
  type        = number
  default     = 5
}
