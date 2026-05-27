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

## 2026-05-27

### Completado
- [x] **dbt configurado completo**:
  - `dbt_project.yml`, `profiles.yml` (con `env_var()` para local y Docker), `packages.yml`
  - `dbt deps` → `dbt_utils 1.3.3` instalado
  - `dbt debug` → All checks passed
  - `dbt seed` → `dim_plans` cargado (4 filas)
- [x] **Capa Silver — Staging** (8 modelos, 25 tests, PASS=25):
  - `stg_customers`, `stg_companies`, `stg_subscriptions`, `stg_payments`
  - `stg_product_events`, `stg_marketing_leads`, `stg_nps_surveys`, `stg_support_tickets`
- [x] **Capa Silver — Intermediate** (3 modelos, 8 tests, PASS=8):
  - `int_customer_lifecycle`, `int_subscription_metrics`, `int_product_engagement`
- [x] **Capa Gold — Marts** (7 modelos, 21 tests, PASS=21):
  - `finance/`: `fct_mrr`, `fct_revenue_expansion`
  - `growth/`: `fct_customer_acquisition`, `fct_activation_funnel`
  - `retention/`: `fct_churn`, `fct_cohort_retention`, `fct_ltv`
- [x] **54 dbt tests pasando** en total (staging + intermediate + marts)
- [x] **Airflow configurado con Astro CLI**:
  - `airflow/Dockerfile` — 3 ENV vars añadidas (`PROJECT_ROOT`, `DBT_PROJECT_DIR`, `DBT_PROFILES_DIR`)
  - `airflow/requirements.txt` — deps de dbt + duckdb para el contenedor
  - `airflow/dags/dag_full_pipeline.py` — DAG completo Bronze → Silver → Gold, schedule `0 6 * * *`
  - `airflow/airflow_settings.yaml` — 3 variables Airflow inyectadas al arrancar
  - `airflow/docker-compose.override.yml` — monta proyecto en `/usr/local/airflow/project`
  - `airflow/.env` — `DUCKDB_PATH` para el contenedor
  - DAG de ejemplo de Astronomer eliminado
- [x] **Airflow corriendo** — UI en `http://airflow.localhost:6563`
- [x] Commit `9479c17` — Silver y Gold layers (32 archivos, 1,019 inserciones)

### Decisiones técnicas
- **`FROM bronze.tabla`** en staging en lugar de `{{ source() }}` — tablas Bronze creadas directamente por Python en DuckDB, no vía dbt sources
- **`env_var('DUCKDB_PATH', fallback_docker)`** en `profiles.yml` — un solo archivo funciona en local (lee `.env`) y en Docker (lee `airflow/.env`); el fallback apunta al path del contenedor
- **`docker-compose.override.yml`** para montar el proyecto en el contenedor — Astro CLI solo monta `airflow/`; sin el override, `PROJECT_ROOT` no existe dentro del Docker
- **Imports Airflow 3.x**: `airflow.providers.standard.operators.bash/empty` en lugar de `airflow.operators.*` (deprecado en runtime 3.2)
- **`dbt/.user.yml`**: archivo auto-generado por dbt con UUID local — nunca commitear, añadido a `.gitignore`

### Problemas resueltos y cómo

| Problema | Causa | Solución |
|---|---|---|
| `dbt/.user.yml` en staging | dbt lo genera automáticamente al correr cualquier comando | Detectado antes del commit, añadido a `.gitignore` y sacado del stage con `git restore --staged` |
| `payment_status` values — `data_sources.md` decía `success` pero los tests pasaron con `paid` | El mock data generator usó `paid` en lugar de `success` | Verificado con `SELECT DISTINCT status FROM bronze.payments` antes de escribir el `schema.yml` — los valores reales del Bronze mandan |
| `int_customer_lifecycle` podría romper test `unique` si un customer tiene >1 suscripción activa | El JOIN con `stg_subscriptions WHERE status='active'` duplicaría filas | Verificado con query explícita: ningún customer tiene >1 suscripción activa → test seguro |
| `schema.yml` de marts con entrada rota `- na_ltv` | Typo en el prompt original (faltaba `name:`) y ubicado en `finance/` siendo que `fct_ltv` va en `retention/` | Corregido a `- name: fct_ltv` y movido a `retention/schema.yml` donde corresponde |
| `dbt debug` fallaba sin `DUCKDB_PATH` exportada localmente | `env_var()` tomaba el fallback Docker (`/usr/local/airflow/project/...`) que no existe en local | Solución: `export $(grep -v '^#' .env | xargs)` antes de cualquier comando `dbt` en local |
| `ingest_billing` fallaba en Airflow con `cd: /usr/local/airflow/project: No such file or directory` | Astro CLI solo monta `airflow/` en el contenedor; `src/` y `dbt/` viven en el directorio padre | Creado `airflow/docker-compose.override.yml` que monta el proyecto raíz en `/usr/local/airflow/project` en los servicios `scheduler`, `dag-processor` y `triggerer` |
| Warnings de imports deprecados en Airflow 3.x | `airflow.operators.bash` y `airflow.operators.empty` están deprecados en runtime 3.2 | Actualizados a `airflow.providers.standard.operators.bash/empty` en `dag_full_pipeline.py` |
| `docker-compose.override.yml` warning `version is obsolete` | Docker Compose moderno ignora el campo `version:` | Eliminada la línea `version: "3.1"` del override |

---

## Pendiente

### Airflow — verificación y ejecución
- [ ] Actualizar `dbt/profiles.yml` con `env_var()` *(hecho localmente, pendiente verificar en contenedor)*
- [ ] Verificar DAG completo en `http://airflow.localhost:6563`
- [ ] Ejecutar pipeline completo desde Airflow (trigger manual)

### Código fuente (`src/`)
- [ ] `src/quality/quality_report.py`

### Notebooks
- [ ] `01_bronze_ingestion.ipynb`
- [ ] `02_silver_transformation.ipynb`
- [ ] `03_gold_kpis.ipynb`
- [ ] `04_exploratory_analysis.ipynb`

### Documentación & publicación
- [ ] `README.md` profesional con diagrama de arquitectura
- [ ] Cuenta GitHub + push del repositorio

### Producción
- [ ] Cuenta Databricks + migración (cambio de `.env` únicamente)
