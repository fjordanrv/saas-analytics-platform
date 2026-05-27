# SaaS Analytics Platform — CloudMetrics Inc.

## ENTORNO VIRTUAL
> **ENTORNO VIRTUAL: usar SIEMPRE `/home/fjordan/Documentos/Estudios/Sport Data Campus/ml-env`**
> **NUNCA crear un entorno virtual nuevo dentro del proyecto.**

```bash
source "/home/fjordan/Documentos/Estudios/Sport Data Campus/ml-env/bin/activate"
```

## Stack
- **Python 3.12** — venv externo: `/home/fjordan/Documentos/Estudios/Sport Data Campus/ml-env`
- **DuckDB 1.5.3** — base de datos local (reemplaza Databricks en dev)
- **dbt-duckdb 1.9.4** — transformaciones Bronze → Silver → Gold
- **Airflow vía Astro CLI** — orquestación (`airflow/` gestionado por Astro)
- **Docker** — Airflow corre en contenedor, runtime `astrocrpublic.azurecr.io/runtime:3.2-4`

## Comandos clave
```bash
# Airflow (Astro)
cd airflow && astro dev start          # levanta Airflow en Docker
cd airflow && astro dev stop
cd airflow && astro dev ps             # UI: http://localhost:8080

# dbt
cd dbt && dbt run --profiles-dir . --target dev
cd dbt && dbt test --profiles-dir . --target dev

# Pipeline Python
python -m src.ingestion.generate_mock_data
python -m src.quality.quality_report
```

## Estructura
```
saas-analytics-platform/
├── airflow/dags/     # DAGs de Airflow
├── data/             # raw/ bronze/ silver/ gold/ — gitignoreados
├── dbt/models/       # staging/ → intermediate/ → marts/
├── src/ingestion/    # scripts Python → Bronze
├── src/quality/      # data quality checks
├── src/utils/        # database.py, logger.py
└── docs/             # data_sources.md, kpi_definitions.md, architecture.md
```

## Convenciones
- **SQL**: CTEs en `snake_case`, comentarios de negocio (el por qué, no el qué)
- **Python**: type hints obligatorios, docstring en clases, logging con `loguru`
- **dbt**: staging=view, intermediate=table, marts=table; una macro por KPI
- **Capas**: Bronze = raw + metadata; Silver = limpio + tipado; Gold = KPIs
- **DuckDB path**: `./data/cloudmetrics.duckdb` (variable `DUCKDB_PATH` en `.env`)
- **Airflow deps**: van en `airflow/requirements.txt`, no en el raíz

## Contexto de negocio
- **Empresa**: CloudMetrics Inc. — SaaS B2B ficticia, modelo de suscripción MRR
- **Arquitectura**: pipeline Medallion Bronze → Silver (dbt) → Gold (dbt)
- **Dev → Prod**: cambiar `.env` — DuckDB local → Databricks cloud, sin tocar código
- Ver `docs/` para fuentes de datos, KPIs y diagrama de arquitectura completos
