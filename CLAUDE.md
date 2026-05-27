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

### Entorno virtual (siempre activar primero)
```bash
source "/home/fjordan/Documentos/Estudios/Sport Data Campus/ml-env/bin/activate"
```

### Python pipeline (desde raíz del proyecto)
```bash
python -m src.ingestion.generate_mock_data
python -m src.ingestion.crm_ingestion
python -m src.ingestion.billing_ingestion
python -m src.ingestion.product_events_ingestion
python -m src.ingestion.marketing_ingestion
python -m src.ingestion.cs_ingestion
```

### dbt (desde carpeta dbt/ con .env cargado)
```bash
export $(grep -v '^#' ../.env | xargs)
dbt debug
dbt seed
dbt run --select staging
dbt run --select intermediate
dbt run --select marts
dbt test
dbt docs generate && dbt docs serve
```

### Airflow (desde carpeta airflow/)
```bash
astro dev start      # levantar
astro dev stop       # parar
astro dev restart    # reiniciar
astro dev logs       # ver logs
# UI: http://airflow.localhost:6563
# Usuario: admin / Password: admin
```

### Git
```bash
git add . && git status
git commit -m "mensaje"
git log --oneline
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

---

## CONTEXTO DE CONTINUIDAD

### Estado actual por capa (2026-05-27)

| Capa | Estado | Detalle |
|------|--------|---------|
| **Bronze** | ✅ Completo | 8 tablas, 79,342 filas, 100% quality score |
| **Silver — Staging** | ✅ Completo | 8 views, 25 tests pasando |
| **Silver — Intermediate** | ✅ Completo | 3 tables, 8 tests pasando |
| **Gold — Marts** | ✅ Completo | 7 tables, 21 tests pasando |
| **Airflow** | ✅ Configurado | Corriendo en `http://airflow.localhost:6563` |
| **Pipeline end-to-end** | ⏳ Pendiente | DAG creado, falta ejecución completa verificada |

### Próximos pasos (en orden)
1. Trigger manual del DAG `saas_analytics_full_pipeline` en la UI y verificar las 9 tareas
2. Crear `src/quality/quality_report.py`
3. Crear 4 notebooks Jupyter (`01_bronze`, `02_silver`, `03_gold`, `04_exploratory`)
4. Escribir `README.md` profesional con diagrama de arquitectura
5. Crear cuenta GitHub y hacer push del repositorio
6. Crear cuenta Databricks y migrar (solo cambio de `.env`)

### Decisiones de diseño tomadas (no revertir)
- **`FROM bronze.tabla`** en staging — tablas Bronze las crea Python en DuckDB directamente; no usar `{{ source() }}`
- **`env_var('DUCKDB_PATH', fallback_docker)`** en `profiles.yml` — el fallback apunta al path Docker; local requiere `export $(grep -v '^#' .env | xargs)` antes de `dbt`
- **`docker-compose.override.yml`** — Astro CLI solo monta `airflow/`; el override monta el proyecto raíz en `/usr/local/airflow/project` en los contenedores `scheduler`, `dag-processor` y `triggerer`
- **Imports Airflow 3.x** — usar `airflow.providers.standard.operators.bash/empty`, no `airflow.operators.*` (deprecado en runtime 3.2)
- **`dbt/.user.yml`** — auto-generado por dbt, en `.gitignore`, nunca commitear
- **Staging lee Bronze por schema** — `bronze.customers`, `bronze.payments`, etc. El schema `bronze` lo crea Python en DuckDB

### Convenciones acordadas
- **SQL**: CTEs en `snake_case`, grain documentado en comentario al inicio del modelo
- **Python**: type hints obligatorios, docstring en clases, `loguru` para logging
- **dbt**: `staging=view`, `intermediate=table`, `marts=table`; schema.yml con tests en cada modelo
- **Tests mínimos por modelo**: `not_null` + `unique` en PKs, `accepted_values` en enums
- **Airflow deps**: siempre en `airflow/requirements.txt`, nunca en el raíz
- **Entorno virtual**: SIEMPRE el externo (`ml-env`); NUNCA crear uno dentro del proyecto
