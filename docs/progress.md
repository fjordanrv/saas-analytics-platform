# Progress — SaaS Analytics Platform
Última actualización: 2026-05-27

## Estado actual: Pipeline completo funcionando en Airflow

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

## Pendiente ⬜

### Próxima sesión (empezar aquí)
1. 4 notebooks Jupyter con análisis exploratorio
   - 01_bronze_ingestion.ipynb
   - 02_silver_transformation.ipynb
   - 03_gold_kpis.ipynb
   - 04_exploratory_analysis.ipynb

2. README.md profesional
   - Badges de tecnologías
   - Diagrama arquitectura Mermaid
   - Tabla de KPIs
   - Quickstart en 3 comandos
   - Screenshots del proyecto

3. GitHub
   - Crear cuenta
   - git remote add origin
   - git push

4. Databricks Community Edition
   - Crear cuenta
   - Actualizar .env: DB_TYPE=databricks
   - Actualizar profiles.yml target: prod
   - Migrar tablas Bronze a Delta Tables

5. Dashboards
   - Figma/Canva con KPIs de Gold layer
   - Screenshots para LinkedIn

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
