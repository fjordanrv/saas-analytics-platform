"""
DAG: saas_analytics_full_pipeline
Descripción: Pipeline diario completo de CloudMetrics Inc.
             Bronze → Silver → Gold
Schedule: 6am UTC todos los días
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.empty import EmptyOperator

PROJECT_ROOT = "/usr/local/airflow/project"
DBT_DIR = f"{PROJECT_ROOT}/dbt"

default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "depends_on_past": False,
}

with DAG(
    dag_id="saas_analytics_full_pipeline",
    default_args=default_args,
    description="Pipeline completo CloudMetrics: Bronze → Silver → Gold",
    schedule="0 6 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["saas", "analytics", "cloudmetrics", "medallion"],
    doc_md="""
    ## SaaS Analytics Full Pipeline — CloudMetrics Inc.

    ### Arquitectura Medallion
    - **Bronze**: Python ingesta desde data/raw/ a DuckDB
    - **Silver**: dbt staging + intermediate
    - **Gold**: dbt marts con KPIs finales

    ### KPIs generados
    - Finance: MRR, ARR, NRR
    - Growth: Activation Rate, CAC, Conversion Rate
    - Retention: Churn Rate, Cohort Retention, LTV
    """,
) as dag:

    start = EmptyOperator(task_id="start")

    ingest_crm = BashOperator(
        task_id="ingest_crm",
        bash_command=f"cd {PROJECT_ROOT} && python -m src.ingestion.crm_ingestion",
    )

    ingest_billing = BashOperator(
        task_id="ingest_billing",
        bash_command=f"cd {PROJECT_ROOT} && python -m src.ingestion.billing_ingestion",
    )

    ingest_events = BashOperator(
        task_id="ingest_product_events",
        bash_command=f"cd {PROJECT_ROOT} && python -m src.ingestion.product_events_ingestion",
    )

    ingest_marketing = BashOperator(
        task_id="ingest_marketing",
        bash_command=f"cd {PROJECT_ROOT} && python -m src.ingestion.marketing_ingestion",
    )

    ingest_cs = BashOperator(
        task_id="ingest_customer_success",
        bash_command=f"cd {PROJECT_ROOT} && python -m src.ingestion.cs_ingestion",
    )

    dbt_staging = BashOperator(
        task_id="dbt_run_staging",
        bash_command=f"cd {DBT_DIR} && dbt run --select staging --profiles-dir .",
    )

    dbt_intermediate = BashOperator(
        task_id="dbt_run_intermediate",
        bash_command=f"cd {DBT_DIR} && dbt run --select intermediate --profiles-dir .",
    )

    dbt_marts = BashOperator(
        task_id="dbt_run_marts",
        bash_command=f"cd {DBT_DIR} && dbt run --select marts --profiles-dir .",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test --profiles-dir .",
    )

    pipeline_success = EmptyOperator(task_id="pipeline_success")

    # Dependencias — ingestas en SECUENCIA por limitación de DuckDB (una sola conexión)
    start >> ingest_crm >> ingest_billing >> ingest_events >> ingest_marketing >> ingest_cs >> dbt_staging

    dbt_staging >> dbt_intermediate
    dbt_intermediate >> dbt_marts
    dbt_marts >> dbt_test
    dbt_test >> pipeline_success
