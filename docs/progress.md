# Progress — SaaS Analytics Platform
Última actualización: 2026-05-28

## Estado actual: Pipeline completo + notebooks + GitHub publicado

## Completado ✅

### Infraestructura
- Estructura de carpetas del proyecto
- Entorno virtual ml-env configurado
- Docker y Astro CLI instalados
- .env, .gitignore, requirements.txt
- CLAUDE.md con contexto del proyecto
- docs/ con arquitectura, KPIs y fuentes de datos

### Datos Mock
- generate_mock_data.py con Faker
- 8 archivos en data/raw/
- 81,842 filas generadas con distribuciones reales

### Bronze Layer (Python)
- src/utils/logger.py — logging centralizado Loguru
  NOTA: detecta Docker vs local automáticamente
- src/utils/database.py — Singleton DuckDB/Databricks
- src/quality/data_quality_checks.py — 5 checks
- src/ingestion/crm_ingestion.py
- src/ingestion/billing_ingestion.py
- src/ingestion/product_events_ingestion.py
- src/ingestion/marketing_ingestion.py
- src/ingestion/cs_ingestion.py
- 8 tablas en DuckDB, 100% quality score

### Silver Layer (dbt)
- 8 modelos staging (vistas) — 25 tests
- 3 modelos intermediate (tablas) — 8 tests
- dbt_project.yml, profiles.yml, packages.yml
- profiles.yml usa env_var() para DuckDB/Databricks
- seeds/dim_plans.csv

### Gold Layer (dbt marts)
- marts/finance: fct_mrr, fct_revenue_expansion
- marts/growth: fct_customer_acquisition, fct_activation_funnel
- marts/retention: fct_churn, fct_cohort_retention, fct_ltv
- 21 tests — Total: 54 dbt tests pasando

### Airflow
- Astro CLI con Docker funcionando
- dag_full_pipeline.py — 11 tareas
- Ingestas en SECUENCIA (DuckDB no soporta paralelo)
- dbt en secuencia: staging → intermediate → marts → test
- docker-compose.override.yml con volumen montado
- Permisos chmod 777 en data/, dbt/, logs/
- Pipeline corriendo exitosamente end-to-end
- UI: http://airflow.localhost:6563

### Git
- 4 commits limpios en rama main
- Sin datos sensibles ni archivos de entorno

### GitHub
- Repositorio público en github.com/fjordanrv/saas-analytics-platform
- 12 commits limpios en main
- README con badges, Mermaid diagram, KPI table
- 4 notebooks pre-ejecutados subidos

### Screenshots
- Carpeta docs/screenshots/ creada
- Ignorada en .gitignore

### Notebooks Jupyter
- 01_bronze_ingestion.ipynb — ✅ completo y pre-ejecutado
- 02_silver_transformation.ipynb — ✅ completo y pre-ejecutado (2026-05-28)
  - 33 celdas, 0 errores, dbt run staging PASS=8, intermediate PASS=3, 33 tests
- 03_gold_kpis.ipynb — ✅ completo y pre-ejecutado (2026-05-28)
  - 33 celdas, 0 errores, 18 charts HTML, 5 MB
  - dbt run marts: PASS=7, dbt test: 21/21 passing
  - KPIs reales: MRR $25,551 · ARR $306,612 · Cohort M12 avg 91.5% · Activation 67%
  - build_notebook_03.py usa patrón .replace() para setup (no f-string escaping)
- 04_exploratory_analysis.ipynb — ✅ completo y pre-ejecutado (2026-05-28)
  - 28 celdas, 0 errores, 7 charts HTML, ~5 MB
  - 5 business questions: Channel LTV/CAC, Churn Timing, Feature Adoption, NPS, Cohort Quality
  - Sección Airflow con ASCII DAG + pipeline metrics table
  - Key Takeaways por equipo (Growth, CS, Product, Finance)
  - build_notebook_04.py con columnas verificadas contra schema real

## Pendiente ⬜

### Próxima sesión (empezar aquí)
1. dbt docs — generar y tomar capturas:
   cd dbt && dbt docs generate && dbt docs serve
   Capturar en http://localhost:8080:
   - Lineage Graph completo → dbt_lineage_graph.png
   - fct_mrr model abierto → dbt_fct_mrr_model.png
   - 54 tests en verde → dbt_tests_passing.png
   Guardar en docs/screenshots/

2. Notebooks — tomar capturas:
   - 03_gold_kpis: cohort heatmap → notebook_03_cohort_heatmap.png
   - 03_gold_kpis: MRR waterfall → notebook_03_mrr_waterfall.png
   - 02_silver: dbt run output → notebook_02_dbt_run.png
   - 04_exploratory: scatter CAC vs LTV → notebook_04_cac_ltv.png

3. Databricks Community Edition:
   - Crear cuenta en databricks.com/try
   - Obtener DATABRICKS_HOST y DATABRICKS_TOKEN
   - Actualizar .env: DB_TYPE=databricks
   - Actualizar dbt/profiles.yml target: prod
   - Migrar tablas Bronze a Delta Tables
   - Re-ejecutar dbt pipeline en Databricks
   - Volver a paralelizar ingestas en Airflow DAG
   - Tomar captura Airflow en paralelo y en verde

4. Post LinkedIn:
   - Imagen principal: cohort heatmap notebook 03
   - Carousel con todas las capturas
   - Descripción del proyecto y stack

## Lecciones aprendidas importantes

### DuckDB limitación de concurrencia
DuckDB solo permite UNA conexión simultánea.
En Airflow las ingestas corren en SECUENCIA.
Cuando migremos a Databricks → se pueden paralelizar.

### Docker permisos
El contenedor Docker necesita permisos de escritura
en las carpetas del proyecto montadas como volumen:
chmod -R 777 data/ dbt/ logs/

### dbt con variables de entorno
Siempre cargar .env antes de correr dbt local:
export $(grep -v '^#' ../.env | xargs)
O usar: cd dbt && dbt run --profiles-dir .

### Airflow logger en Docker
logger.py detecta /usr/local/airflow para saber
si está en Docker y usa /tmp/airflow_logs en lugar
de logs/ del proyecto.
