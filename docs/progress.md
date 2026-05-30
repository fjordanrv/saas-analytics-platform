# Progress — SaaS Analytics Platform
Última actualización: 2026-05-30

## Estado actual: Pipeline completo + AEGIS AI Dashboard diseñado ✅

---

## Completado ✅

### Infraestructura
- Estructura de carpetas, ml-env (Python 3.12), Docker, Astro CLI
- .env, .gitignore, requirements.txt, CLAUDE.md, docs/
- kaleido 1.3.0 en ml-env (export PNG Plotly)

### Datos Mock
- generate_mock_data.py con Faker · 8 archivos en data/raw/ · 79,842 filas Bronze

### Bronze Layer (Python)
- src/utils/logger.py, database.py (Singleton DuckDB/Databricks), data_quality_checks.py
- 5 scripts de ingesta (crm, billing, product_events, marketing, cs)
- `write_dataframe()` en DatabaseConnection — despacha a DuckDB o Databricks según DB_TYPE
- 8 tablas Bronze en DuckDB (dev) y Databricks Delta Tables (prod)

### Silver Layer (dbt)
- 8 modelos staging (vistas) · 3 modelos intermediate (tablas) · 25+8 tests
- profiles.yml: dev=DuckDB / prod=Databricks via env_var()
- `compat_datediff` macro: compatibilidad DuckDB↔Databricks
- seeds/dim_plans.csv

### Gold Layer (dbt marts)
- marts/finance: fct_mrr, fct_revenue_expansion
- marts/growth: fct_customer_acquisition, fct_activation_funnel
- marts/retention: fct_churn, fct_cohort_retention, fct_ltv
- 21 tests Gold · 54 dbt tests totales pasando en dev Y prod

### Airflow
- Astro CLI + Docker · dag_full_pipeline.py · UI: http://airflow.localhost:6563
- **5 ingestas en PARALELO** (Databricks soporta múltiples conexiones)
- dbt en secuencia: staging → intermediate → marts → test (todos --target prod)
- docker-compose.override.yml: env vars Databricks + AIRFLOW_HOME override

### Notebooks Jupyter (4 pre-ejecutados, 0 errores)
- 01_bronze_ingestion.ipynb, 02_silver_transformation.ipynb
- 03_gold_kpis.ipynb — MRR $25,551 · ARR $306,612 · Cohort M12 91.5% · Activation 63.9%
- 04_exploratory_analysis.ipynb — 5 business questions, Key Takeaways por equipo

### Screenshots (docs/screenshots/ — no trackeadas en git)
- dbt_lineage_graph.png · dbt_fct_mrr_model.png · dbt_tests_passing.png
- notebook_03_mrr_waterfall.png · notebook_03_cohort_heatmap.png
- notebook_02_dbt_run.png · notebook_04_cac_ltv.png
- airflow_parallel_green.png (captura pipeline paralelo en verde)

### GitHub
- github.com/fjordanrv/saas-analytics-platform · 15 commits en main
- README profesional con badges, diagrama Mermaid, tabla KPIs · 4 notebooks subidos

### Databricks (2026-05-29 — COMPLETADO)
- Cuenta: dbc-6f3f61b1-f9c3.cloud.databricks.com (Free Edition)
- Catálogo `saas_platform`: schemas bronze, staging, intermediate, finance, growth, retention, seeds
- Unity Catalog Volume: `saas_platform.bronze.raw_files`
- 79,842 filas migradas como Delta Tables vía Parquet + Volume + COPY INTO
- `dbt run --target prod` → 18/18 modelos PASS
- `dbt test --target prod` → 54/54 tests PASS
- Pipeline ingesta Databricks: 8/8 tablas, 100% quality score, ~6s/tabla

### dbt schemas limpios (2026-05-30)
- Macro `generate_schema_name.sql` creada en `dbt/macros/`
- Schemas Gold sin prefijos: `finance`, `retention`, `growth`, `intermediate`, `staging`, `seeds`, `bronze`
- `dbt run --target prod` → 18/18 PASS con nombres de schema correctos

### Tableau / AEGIS AI (2026-05-30 — Fase 1 diseñada)
- Tableau Desktop instalado y conectado a Databricks (`saas_platform` catálogo)
- Archivo `tableau/AEGIS_AI_Executive_Intelligence.twb` creado
- Dashboard AEGIS AI diseñado completamente:
  - Arquitectura: Header · Hero Number · AI Executive Brief · Signal Panel · AI Detection Feed · Forecast Confidence Band
  - Paleta fondo: `#07111F` / `#0E1B2E` / `#0F2040` / `#1A2F4A`
  - Colores acento: `#3B82F6` / `#22D3EE` / `#8B5CF6` / `#00D7A0` / `#FFB547` / `#FF5C5C`
  - Canvas: 1600×900px Fixed
  - Fase 2 pendiente: gradientes y profundidad visual (fondo PNG)

---

## Pendiente ⬜

### Próxima sesión (empezar aquí)
1. **Tableau — construir componentes** en orden:
   - Header (primer componente)
   - Hero Number (MRR, Churn, NRR, LTV)
   - AI Executive Brief
   - Signal Panel
   - AI Detection Feed
   - Forecast Confidence Band
2. **Tableau — Fase 2**: fondo PNG con gradientes ambientales
3. **Publicar** en Tableau Public
4. **Post LinkedIn** — carousel con capturas del proyecto
   - Imagen principal: airflow_parallel_green.png
   - Slides: cohort heatmap, MRR waterfall, dbt lineage, AEGIS AI dashboard

### Stack final confirmado
```
Faker → Bronze (Python) → Silver (dbt) → Gold (dbt) → Databricks Delta Tables → Tableau Public
                                                               ↑
                                                       Airflow (5 ingestas paralelas)
```

---

## Lecciones aprendidas

### DuckDB
- Una sola conexión escritura · `dbt docs serve` bloquea `dbt run` → matar proceso antes
- `duckdb_tables()` usa `schema_name` (no `table_schema`)

### Databricks — fixes críticos
- `DATABRICKS_HOST` sin `https://` — dbt-databricks lo añade internamente; con https → 403
- DBFS root bloqueado en Free Edition → usar Unity Catalog Volumes (`/api/2.0/fs/files`)
- `databricks-sql-connector==4.1.5` (no 3.7.0) — requerido por dbt-databricks==1.12.0
- dbt-core en airflow/requirements.txt: 1.11.8 (compatible con dbt-databricks); no incluir dbt-duckdb

### dbt DuckDB→Databricks compatibilidad
- `datediff('day', ...)` → usar macro `compat_datediff` (quoted en DuckDB, unquoted en Databricks)
- `unnest(range(0,13))` → `{% if target.type == 'databricks' %} explode(sequence(0,12))`

### Airflow + Docker
- `docker-compose.override.yml`: `environment:` tiene precedencia sobre `env_file:` — usar para AIRFLOW_HOME, BASE_LOG_FOLDER, DAGS_FOLDER con paths del contenedor
- `airflow/requirements.txt` separado del requirements.txt raíz — nunca mezclar

### Plotly/Kaleido export PNG
- `template="plotly_dark"` no fiable en headless → setear colores explícitamente en `update_layout`
- Colorscales: extremos brillantes (`#C62828`, `#00E676`) · `xgap=2, ygap=2` · `zmin` dinámico
