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

## Pendiente

### Config & docs
- [ ] `.env` + `.env.example`
- [ ] `.gitignore`
- [ ] `README.md` principal con diagrama de arquitectura
- [ ] `git init` + primer commit

### Código fuente (`src/`)
- [ ] `src/utils/logger.py` — logger con loguru
- [ ] `src/utils/database.py` — conexión DuckDB (singleton, compatible con Databricks)
- [ ] `src/ingestion/generate_mock_data.py` — 1K customers, 50K events, etc.
- [ ] `src/ingestion/crm_ingestion.py`
- [ ] `src/ingestion/billing_ingestion.py`
- [ ] `src/ingestion/product_events_ingestion.py`
- [ ] `src/ingestion/marketing_ingestion.py`
- [ ] `src/quality/data_quality_checks.py`
- [ ] `src/quality/quality_report.py`
- [ ] `__init__.py` en cada módulo

### SQL
- [ ] `sql/bronze/create_bronze_tables.sql`
- [ ] `sql/silver/` — transformaciones por entidad
- [ ] `sql/gold/` — MRR, Churn, LTV, Activation, Cohort

### dbt
- [ ] `dbt/dbt_project.yml` + `profiles.yml` (target DuckDB)
- [ ] `dbt/packages.yml` + `dbt deps`
- [ ] Staging models (5 modelos — views sobre Bronze)
- [ ] Intermediate models (3 modelos)
- [ ] Mart models: finance (fct_mrr, fct_nrr), growth (fct_activation), retention (fct_churn, fct_cohort, fct_ltv)
- [ ] Tests y macros

### Airflow
- [ ] DAG principal (`dag_full_pipeline.py`)
- [ ] DAGs individuales por capa
- [ ] `airflow_settings.yaml` con conexión DuckDB

### Notebooks
- [ ] `01_bronze_ingestion.ipynb`
- [ ] `02_silver_transformation.ipynb`
- [ ] `03_gold_kpis.ipynb`
- [ ] `04_exploratory_analysis.ipynb`
