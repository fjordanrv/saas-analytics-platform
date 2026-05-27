# Progress — SaaS Analytics Platform

## 2026-05-22

### Completado
- [x] Estructura de carpetas creada (27 directorios, sin archivos)
- [x] Entorno virtual `ml-env` (Python 3.12.3) verificado y completado:
  - Instalados: `faker`, `duckdb 1.5.3`, `sqlalchemy`, `loguru`, `dbt-core 1.9.4`, `dbt-duckdb 1.9.4`
  - Ya existían: `pandas`, `numpy`, `plotly`, `rich`, `python-dotenv`, `jupyter`
- [x] Docker verificado: v29.5.0 + Compose v5.1.3
- [x] Astro CLI instalado (Airflow gestionado vía Astro)
- [x] `airflow/` inicializado por Astro CLI con Dockerfile, dags/, settings
- [x] `requirements.txt` raíz creado (versiones pinneadas del entorno)
- [x] `airflow/requirements.txt` actualizado con deps de dbt + duckdb para el contenedor
- [x] `CLAUDE.md` creado (59 líneas) — stack, comandos, estructura, convenciones

### Decisiones de arquitectura
- **DuckDB** como motor local en lugar de Databricks (swap sin cambiar código: solo `.env`)
- **Astro CLI** para Airflow en lugar de docker-compose manual
- **Airflow runtime**: `astrocrpublic.azurecr.io/runtime:3.2-4`

---

## 2026-05-23

### Completado
- [x] `docs/data_sources.md` creado — 5 fuentes de datos con todos sus campos, tipos y notas de modelado:
  - CRM: `customers` (14 campos) + `companies` (6 campos)
  - Product Events: `product_events` (8 campos), distribución de event_types, definición de sesión (30 min)
  - Billing: `subscriptions` (10 campos) + `payments` (8 campos), modelo de upgrade Opción A
  - Marketing: `marketing_leads` (9 campos), atribución last touch, CAC por canal
  - Customer Success: `nps_surveys` (7 campos) + `tickets` (8 campos), fórmula Health Score
- [x] `docs/kpi_definitions.md` creado — 6 dominios, 17 KPIs con fórmula, granularidad, owner y benchmark:
  - Revenue: MRR (5 componentes), ARR, NRR
  - Retention: Churn Rate, Logo vs Revenue Churn, Cohort Retention
  - Growth: New Customers, Activation Rate (3 pasos / 14 días), Conversion Rate, CAC
  - Product: DAU/MAU/Stickiness, Feature Adoption Rate, Engagement Score (4 componentes)
  - Customer Success: NPS + response_rate_pct, Health Score, TTR por prioridad, Customers at Risk
  - LTV: LTV, LTV por segmento, LTV/CAC, Payback Period
- [x] `docs/architecture.md` creado — diagrama Mermaid end-to-end + descripción de capas, orquestación y entornos
- [x] `CLAUDE.md` refactorizado a 55 líneas — eliminado el contexto verboso, agregada sección corta con punteros a `docs/`

### Decisiones de diseño
- **CLAUDE.md corto (≤ 60 líneas)**: solo stack, comandos y convenciones; el detalle vive en `docs/`
- **docs/ como fuente de verdad**: `data_sources.md`, `kpi_definitions.md` y `architecture.md` son los documentos de referencia del negocio

---

---

## 2026-05-24

### Completado
- [x] `.env` + `.env.example` creados — DB_TYPE, DUCKDB_PATH, vars Databricks vacías, dbt/Airflow/GitHub config
- [x] `.gitignore` creado — cubre `.env`, `data/`, `*.duckdb`, Python, dbt, Airflow, Jupyter, IDE, logs
- [x] `src/utils/logger.py` — logger Loguru con formato enriquecido, rotación diaria, bind por módulo, fix `TYPE_CHECKING` para `Logger` type hint
- [x] `src/utils/database.py` — singleton `DatabaseConnection`, soporte DuckDB + Databricks (dispatch por `DB_TYPE`), métodos `execute`, `execute_df`, `create_schema`
- [x] `src/__init__.py`, `src/utils/__init__.py`, `src/ingestion/__init__.py`, `src/quality/__init__.py` creados
- [x] `src/ingestion/generate_mock_data.py` — 79,342 filas en 8 CSVs + product_events.json:
  - `crm_companies.csv` (500), `crm_customers.csv` (1,000)
  - `billing_subscriptions.csv` (1,000), `billing_payments.csv` (22,842)
  - `product_events.csv` (50,000) — timestamps vectorizados, 70% weekday, 60% biz hours
  - `marketing_leads.csv` (3,000), `nps_surveys.csv` (1,500), `support_tickets.csv` (1,000)
- [x] `src/quality/data_quality_checks.py` — `DataQualityChecker` con method chaining:
  - `check_nulls`, `check_duplicates`, `check_value_ranges`, `check_referential_integrity`, `check_date_consistency`
  - `QualityReport.print_summary()` con tabla Rich (fix `escape()` para markup de columnas)
- [x] `src/ingestion/crm_ingestion.py` → `bronze.companies` (500) + `bronze.customers` (1,000)
- [x] `src/ingestion/billing_ingestion.py` → `bronze.subscriptions` (1,000) + `bronze.payments` (22,842)
- [x] `src/ingestion/product_events_ingestion.py` → `bronze.product_events` (50,000)
- [x] `src/ingestion/marketing_ingestion.py` → `bronze.marketing_leads` (3,000)
- [x] `src/ingestion/cs_ingestion.py` → `bronze.nps_surveys` (1,500) + `bronze.support_tickets` (1,000)
- [x] **Capa Bronze completa** — 8 tablas, 79,342 filas, 100% quality score en todas
- [x] `git init` + primer commit (`95a24de`) — 33 archivos, 3,965 inserciones

### Decisiones técnicas
- **`conn.register("_bronze_tmp", df)` + `CREATE OR REPLACE TABLE`**: patrón para insertar DataFrames en DuckDB sin dependencia de SQLAlchemy
- **`from __future__ import annotations` + `TYPE_CHECKING`**: necesario para que Loguru's `Logger` type hint no falle en runtime (loguru 0.7.3 solo exporta `Logger` en stubs `.pyi`)
- **`pd.Series()` wrapper** sobre `DatetimeIndex` para habilitar el accessor `.dt` en generación vectorizada de eventos
- **Patrón ingesta unificado**: `read_source → validate_schema → quality_checks → add_bronze_metadata → write_bronze` replicado en los 5 scripts

---

## Pendiente

### Config & docs
- [ ] `README.md` principal con diagrama de arquitectura

### dbt
- [ ] `dbt/dbt_project.yml` + `profiles.yml` (target DuckDB)
- [ ] `dbt/packages.yml` + `dbt deps`
- [ ] Staging models — 7 views sobre Bronze:
  - `stg_customers`, `stg_companies`
  - `stg_subscriptions`, `stg_payments`
  - `stg_product_events`, `stg_marketing_leads`
  - `stg_nps_surveys`, `stg_support_tickets`
- [ ] Intermediate models:
  - `int_customer_activity`, `int_subscription_movements`, `int_marketing_attribution`
- [ ] Mart models:
  - `finance/`: `fct_mrr`, `fct_nrr`
  - `growth/`: `fct_activation`, `fct_new_customers`
  - `retention/`: `fct_churn`, `fct_cohort`, `fct_ltv`
  - `product/`: `fct_engagement`, `fct_feature_adoption`
  - `customer_success/`: `fct_health_score`, `fct_nps`, `fct_ttr`
- [ ] Tests (`not_null`, `unique`, `accepted_values`, `relationships`) y macros

### Airflow
- [ ] DAG principal (`dag_full_pipeline.py`)
- [ ] DAGs individuales por capa
- [ ] `airflow_settings.yaml` con conexión DuckDB

### Código fuente (`src/`)
- [ ] `src/quality/quality_report.py`

### Notebooks
- [ ] `01_bronze_ingestion.ipynb`
- [ ] `02_silver_transformation.ipynb`
- [ ] `03_gold_kpis.ipynb`
- [ ] `04_exploratory_analysis.ipynb`
