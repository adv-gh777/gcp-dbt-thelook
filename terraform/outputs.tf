output "dbt_service_account" {
  value = google_service_account.dbt.email
}

output "datasets" {
  value = [for d in google_bigquery_dataset.layer : d.dataset_id]
}
