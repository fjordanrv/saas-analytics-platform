# SaaS Analytics Platform — CloudMetrics Inc.

## ENTORNO VIRTUAL
> **SIEMPRE: `/home/fjordan/Documentos/Estudios/Sport Data Campus/ml-env`**
> **NUNCA crear un entorno virtual nuevo dentro del proyecto.**

```bash
source "/home/fjordan/Documentos/Estudios/Sport Data Campus/ml-env/bin/activate"
```

## Stack
- **Python 3.12** · **DuckDB 1.5.3** (dev) · **Databricks Free Edition** (prod) · catálogo `saas_platform`
- **dbt-core 1.11.8** · **dbt-duckdb 1.9.4** · **dbt-databricks 1.12.0** · **databricks-sql-connector 4.1.5**
- **Airflow** vía Astro CLI · **Docker** runtime `astrocrpublic.azurecr.io/runtime:3.2-4`
- **Plotly + Kaleido 1.3.0** · `DB_TYPE` en `.env` controla dev/prod sin tocar código

## Comandos clave
```bash
# Activar entorno
source "/home/fjordan/Documentos/Estudios/Sport Data Campus/ml-env/bin/activate"
# Ingesta Bronze (desde raíz, con .env cargado)
export $(grep -v '^#' .env | xargs)
python -m src.ingestion.crm_ingestion    # idem billing, product_events, marketing, cs
# dbt (desde dbt/ con .env cargado)
dbt run --select staging|intermediate|marts --target prod
dbt test --target prod
# Airflow (desde airflow/)
astro dev start|stop|restart             # UI: http://airflow.localhost:6563 admin/admin
```

## Convenciones
- SQL: CTEs `snake_case` · Python: type hints + loguru · dbt: staging=view, intermediate/marts=table
- Airflow deps: `airflow/requirements.txt` · entorno: SIEMPRE ml-env externo
- Bronze por schema directo: `FROM bronze.tabla` en staging (no `{{ source() }}`)
- Airflow deps: `airflow/requirements.txt`; raíz: `requirements.txt` — nunca mezclar

## CONTEXTO DE CONTINUIDAD — Estado al 2026-05-29

| Capa | Estado | Detalle |
|------|--------|---------|
| **Bronze** | ✅ Completo | 8 Delta Tables Databricks · 79,842 filas · 100% quality |
| **Silver/Gold** | ✅ Completo | 18 modelos dbt · 54/54 tests PASS en prod (Databricks) |
| **Airflow** | ✅ Completo | 5 ingestas paralelas → dbt staging→intermediate→marts→test |
| **Notebooks** | ✅ Completo | 4 pre-ejecutados · 7 PNGs en docs/screenshots/ |
| **GitHub** | ✅ Publicado | github.com/fjordanrv/saas-analytics-platform · 15 commits |
| **Databricks** | ✅ Prod live | write_dataframe() · Unity Catalog Volume raw_files |

## Próximos pasos
1. **Tableau Public** — conectar tablas Gold de Databricks y construir dashboard
2. **Post LinkedIn** — carousel: airflow_parallel_green.png, cohort heatmap, MRR waterfall, dbt lineage

## Decisiones de diseño (no revertir)
- `DATABRICKS_HOST` sin `https://` · DBFS bloqueado en Free → Unity Catalog Volumes (`/api/2.0/fs/files`)
- `write_dataframe()` en `DatabaseConnection` despacha a `_write_duckdb` o `_write_databricks` según `DB_TYPE`
- `compat_datediff` macro: DuckDB `'day'` quoted, Databricks unquoted · `unnest(range)` → `explode(sequence)`
- `docker-compose.override.yml`: `environment:` override `env_file` para `AIRFLOW_HOME=/usr/local/airflow`
- `airflow/requirements.txt`: dbt-core 1.11.8 + databricks-sql-connector 4.1.5 (sin dbt-duckdb)
- DAG: todos los BashOperators dbt usan `--target prod` · ingestas en paralelo con fan-out
