# Progress — SaaS Analytics Platform
Última actualización: 2026-05-28

## Estado actual: Pipeline completo · Databricks conectado · Portfolio publicado

---

## Completado ✅

### Infraestructura
- Estructura de carpetas del proyecto
- Entorno virtual ml-env configurado (Python 3.12)
- Docker y Astro CLI instalados
- .env, .gitignore, requirements.txt
- CLAUDE.md con contexto del proyecto
- docs/ con arquitectura, KPIs y fuentes de datos
- kaleido 1.3.0 instalado en ml-env (export PNG de Plotly)

### Datos Mock
- generate_mock_data.py con Faker
- 8 archivos en data/raw/
- 79,842 filas en Bronze (distribuciones reales de SaaS B2B)

### Bronze Layer (Python)
- src/utils/logger.py — logging centralizado Loguru (detecta Docker vs local)
- src/utils/database.py — Singleton DuckDB/Databricks
- src/quality/data_quality_checks.py — 5 checks, 100% quality score
- src/ingestion/crm_ingestion.py
- src/ingestion/billing_ingestion.py
- src/ingestion/product_events_ingestion.py
- src/ingestion/marketing_ingestion.py
- src/ingestion/cs_ingestion.py
- 8 tablas en DuckDB bronze.*

### Silver Layer (dbt)
- 8 modelos staging (vistas) — 25 tests
- 3 modelos intermediate (tablas) — 8 tests
- dbt_project.yml, profiles.yml, packages.yml
- profiles.yml usa env_var() para DuckDB (dev) / Databricks (prod)
- seeds/dim_plans.csv

### Gold Layer (dbt marts)
- marts/finance: fct_mrr, fct_revenue_expansion
- marts/growth: fct_customer_acquisition, fct_activation_funnel
- marts/retention: fct_churn, fct_cohort_retention, fct_ltv
- 21 tests Gold — 54 dbt tests totales pasando

### Airflow
- Astro CLI con Docker funcionando
- dag_full_pipeline.py — 11 tareas
- Ingestas en SECUENCIA (DuckDB no soporta paralelo)
- dbt en secuencia: staging → intermediate → marts → test
- docker-compose.override.yml con volumen montado
- Pipeline corriendo exitosamente end-to-end
- UI: http://airflow.localhost:6563

### Notebooks Jupyter (4 — todos pre-ejecutados, 0 errores)
- **01_bronze_ingestion.ipynb** — ingesta completa, quality checks, ~5.2 MB
- **02_silver_transformation.ipynb** — dbt staging PASS=8, intermediate PASS=3, 33 tests, 3 charts
- **03_gold_kpis.ipynb** — dbt marts PASS=7, 21 tests, 12 charts KPIs Gold
  - MRR $25,551 · ARR $306,612 · Cohort M12 avg 91.5% · Activation 63.9%
  - Heatmap colorscale corregida (extremos brillantes para Kaleido export)
- **04_exploratory_analysis.ipynb** — 5 business questions, 7 charts, Key Takeaways por equipo

### Screenshots exportadas (docs/screenshots/ — no trackeadas en git)
- dbt_lineage_graph.png — lineage graph completo del pipeline
- dbt_fct_mrr_model.png — modelo fct_mrr en dbt docs
- dbt_tests_passing.png — 54 tests en verde
- notebook_03_mrr_waterfall.png — MRR waterfall con 5 movimientos
- notebook_03_cohort_heatmap.png — cohort retention heatmap (colorscale corregida)
- notebook_02_dbt_run.png — output dbt run Silver layer
- notebook_04_cac_ltv.png — scatter CAC vs LTV por canal

### GitHub
- Repositorio público: github.com/fjordanrv/saas-analytics-platform
- README profesional con badges, diagrama Mermaid, tabla KPIs
- 4 notebooks pre-ejecutados subidos

### Databricks
- Cuenta conectada: dbc-6f3f61b1-f9c3.cloud.databricks.com
- `dbt debug --target prod` → All checks passed ✅
- Catálogo `saas_platform` verificado con schemas: staging, intermediate, finance, growth, retention, seeds
- Fix aplicado: `DATABRICKS_HOST` sin prefijo `https://` en .env

---

## Pendiente ⬜

### Siguiente paso prioritario
1. **`dbt run --target prod`** — migrar modelos Silver+Gold a Databricks Delta Tables
   ```bash
   cd dbt && export $(grep -v '^#' ../.env | xargs)
   dbt run --target prod --select staging
   dbt run --target prod --select intermediate
   dbt run --target prod --select marts
   dbt test --target prod
   ```

2. **Paralelizar ingestas en Airflow** — al migrar a Databricks desaparece la restricción
   de escritura única de DuckDB; cambiar `trigger_rule` en el DAG

3. **Post LinkedIn** — carousel con screenshots del proyecto
   - Imagen principal: cohort heatmap (notebook_03_cohort_heatmap.png)
   - Slides: MRR waterfall, dbt lineage, KPI dashboard, pipeline Airflow

---

## Lecciones aprendidas importantes

### DuckDB — concurrencia y lock
- Solo permite UNA conexión con permisos de escritura simultánea
- `dbt docs serve` abre una conexión y bloquea `dbt run` → matar el proceso antes:
  `lsof data/cloudmetrics.duckdb | awk 'NR>1{print $2}' | xargs kill`
- En notebooks: `run_dbt()` cierra y reabre la conexión DuckDB antes/después de cada subprocess dbt
- `duckdb_tables()` usa `schema_name` (no `table_schema` como en PostgreSQL/SQL estándar)

### Docker permisos
- El contenedor Docker necesita permisos de escritura en carpetas montadas como volumen:
  `chmod -R 777 data/ dbt/ logs/`

### dbt con variables de entorno
- Siempre cargar .env antes de correr dbt local:
  `export $(grep -v '^#' ../.env | xargs)`
- profiles.yml usa `env_var()` — sin las vars exportadas dbt usa el fallback Docker

### Databricks — DATABRICKS_HOST
- El adaptador dbt-databricks espera el hostname SIN `https://`
- El conector Python (`databricks-sql-connector`) acepta ambos formatos
- Con `https://` en dbt → HTTP 403 "Invalid access token" (URL malformada internamente)

### Plotly/Kaleido — export PNG fiel al notebook
- `template="plotly_dark"` no es confiable en Kaleido 1.x headless — setear todos los
  colores explícitamente en `update_layout` (`paper_bgcolor`, `plot_bgcolor`, `gridcolor`)
- Colorscales de heatmaps: usar extremos brillantes (`#C62828` rojo, `#00E676` verde neón)
  — los oscuros (`#8B0000`, `#006400`) se funden con el fondo `#0F1929` en PNG export
- `xgap=2, ygap=2` en `go.Heatmap` — bordes visibles entre celdas en render estático
- `zmin` basado en datos reales (`df.min() - 2`), no en benchmark arbitrario (ej: 60)
