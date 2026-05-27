# Architecture — CloudMetrics Inc.

Pipeline de datos batch con arquitectura Medallion (Bronze → Silver → Gold).
Airflow orquesta todas las capas; DuckDB en desarrollo, Databricks en producción.

---

## Diagrama de arquitectura

```mermaid
flowchart TD
    %% Fuentes externas
    subgraph SOURCES["Fuentes Externas"]
        CRM["CRM\ncompanies / customers"]
        BILLING["Billing\nsubscriptions / payments"]
        PRODUCT["Product Events\nproduct_events"]
        MARKETING["Marketing\nmarketing_leads"]
        CS["Customer Success\nnps_surveys / tickets"]
    end

    %% Ingesta Python → Bronze
    subgraph INGESTION["Ingesta — Python (src/ingestion/)"]
        PY_CRM["crm_ingestion.py"]
        PY_BILLING["billing_ingestion.py"]
        PY_PRODUCT["product_events_ingestion.py"]
        PY_MARKETING["marketing_ingestion.py"]
        PY_CS["cs_ingestion.py"]
    end

    %% Bronze
    subgraph BRONZE["Bronze — Raw + Metadata"]
        B_CRM["bronze.companies\nbronze.customers"]
        B_BILLING["bronze.subscriptions\nbronze.payments"]
        B_PRODUCT["bronze.product_events"]
        B_MARKETING["bronze.marketing_leads"]
        B_CS["bronze.nps_surveys\nbronze.tickets"]
    end

    %% Silver — dbt
    subgraph SILVER["Silver — dbt (staging + intermediate)"]
        STG["Staging (views)\nstg_customers / stg_companies\nstg_subscriptions / stg_payments\nstg_product_events\nstg_marketing_leads\nstg_nps / stg_tickets"]
        INT["Intermediate (tables)\nint_customer_activity\nint_subscription_movements\nint_marketing_attribution"]
    end

    %% Gold — dbt
    subgraph GOLD["Gold — dbt (marts)"]
        FINANCE["finance/\nfct_mrr\nfct_nrr"]
        GROWTH["growth/\nfct_activation\nfct_new_customers"]
        RETENTION["retention/\nfct_churn\nfct_cohort\nfct_ltv"]
        PRODUCT_M["product/\nfct_engagement\nfct_feature_adoption"]
        CS_M["customer_success/\nfct_health_score\nfct_nps\nfct_ttr"]
    end

    %% Dashboards
    subgraph DASHBOARDS["Consumo"]
        DASH["Dashboards\n(BI / Notebooks)"]
    end

    %% Orquestación
    subgraph ORCHESTRATION["Orquestación — Airflow (Astro CLI)"]
        DAG["dag_full_pipeline.py\nBronze → Silver → Gold"]
    end

    %% Motor de datos
    subgraph ENGINE["Motor de Datos"]
        DUCKDB["DuckDB 1.5.3\n(dev — local)"]
        DATABRICKS["Databricks\n(prod — cloud)"]
    end

    %% Flujo principal
    CRM --> PY_CRM --> B_CRM
    BILLING --> PY_BILLING --> B_BILLING
    PRODUCT --> PY_PRODUCT --> B_PRODUCT
    MARKETING --> PY_MARKETING --> B_MARKETING
    CS --> PY_CS --> B_CS

    B_CRM & B_BILLING & B_PRODUCT & B_MARKETING & B_CS --> STG
    STG --> INT
    INT --> FINANCE & GROWTH & RETENTION & PRODUCT_M & CS_M
    FINANCE & GROWTH & RETENTION & PRODUCT_M & CS_M --> DASH

    %% Orquestación
    DAG -.->|"orquesta"| INGESTION
    DAG -.->|"orquesta"| SILVER
    DAG -.->|"orquesta"| GOLD

    %% Motor
    BRONZE -.->|"dev"| DUCKDB
    BRONZE -.->|"prod"| DATABRICKS
    SILVER -.->|"dev"| DUCKDB
    SILVER -.->|"prod"| DATABRICKS
    GOLD -.->|"dev"| DUCKDB
    GOLD -.->|"prod"| DATABRICKS
```

---

## Capas de datos

### Bronze — Raw + Metadata

- **Qué contiene:** datos crudos tal como llegan de la fuente, sin transformar
- **Cómo se pobla:** scripts Python en `src/ingestion/`
- **Formato:** tablas DuckDB con columnas de metadata añadidas:
  - `_ingested_at` — timestamp de ingesta
  - `_source` — nombre de la fuente de origen
- **Política:** append-only, nunca se modifica un registro Bronze

### Silver — Limpio + Tipado

- **Qué contiene:** datos normalizados, con tipos correctos, deduplicados y validados
- **Cómo se pobla:** modelos dbt en `dbt/models/staging/` y `dbt/models/intermediate/`
- **Staging:** views sobre Bronze, renombrado de columnas y casting de tipos
- **Intermediate:** tablas con joins multi-fuente y lógica de negocio

### Gold — KPIs

- **Qué contiene:** métricas de negocio calculadas, listas para consumo
- **Cómo se pobla:** modelos dbt en `dbt/models/marts/`
- **Organización:** un subdirectorio por dominio de KPI
- **Consumidores:** dashboards BI, notebooks de análisis, alertas automáticas

---

## Orquestación

Airflow gestiona la ejecución del pipeline completo de forma diaria.

```
dag_full_pipeline.py
│
├── Task Group: bronze_ingestion
│   ├── ingest_crm
│   ├── ingest_billing
│   ├── ingest_product_events
│   ├── ingest_marketing
│   └── ingest_customer_success
│
├── Task Group: silver_transformation
│   ├── dbt_staging
│   └── dbt_intermediate
│
└── Task Group: gold_kpis
    ├── dbt_marts_finance
    ├── dbt_marts_growth
    ├── dbt_marts_retention
    ├── dbt_marts_product
    └── dbt_marts_customer_success
```

- **Scheduler:** daily @ 02:00 UTC
- **UI:** http://localhost:8080 (dev)
- **Runtime:** `astrocrpublic.azurecr.io/runtime:3.2-4`

---

## Entornos

| Aspecto | Dev | Prod |
|---|---|---|
| Motor SQL | DuckDB 1.5.3 (local) | Databricks (cloud) |
| dbt target | `dev` | `prod` |
| Airflow | Astro CLI + Docker local | Managed Airflow (cloud) |
| Config | `.env` con `DUCKDB_PATH` | Variables de entorno cloud |
| Datos | Mock generados con Faker | Datos reales de clientes |

> El swap Dev → Prod es solo un cambio de `profiles.yml` en dbt y variables de entorno — el código Python y SQL no cambia.

---

## Data Quality

Los checks de calidad se ejecutan después de Bronze y antes de Silver:

- **Python:** `src/quality/data_quality_checks.py` — checks sobre Bronze
- **dbt tests:** `not_null`, `unique`, `accepted_values`, `relationships` sobre Silver
- **Reporte:** `src/quality/quality_report.py` — resumen de resultados por ejecución
