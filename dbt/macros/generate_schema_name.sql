{#
  By default dbt names custom schemas "<target_dataset>_<custom>" (e.g. core_mart).
  Use the custom schema name as-is so models land in the Terraform-managed
  raw / core / mart datasets.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
