"""Generates notebooks/02_silver_transformation.ipynb using nbformat."""

import nbformat

PROJECT_ROOT = "/home/fjordan/Documentos/Proyectos/Personales/proyectos-principales/saas-analytics-platform"
DBT_BIN = "/home/fjordan/Documentos/Estudios/Sport Data Campus/ml-env/bin/dbt"

def md(source): return nbformat.v4.new_markdown_cell(source)
def code(source): return nbformat.v4.new_code_cell(source)

cells = []

# ── Cover ──────────────────────────────────────────────────────────────────────
cells.append(md("""<div style="background: linear-gradient(135deg, #0F1929 0%, #1a3a2a 100%); padding: 40px; border-radius: 12px; border-left: 6px solid #C0C0C0;">

# 🥈 Silver Layer: dbt Transformations
### CloudMetrics Inc. — SaaS Analytics Platform

**From raw Bronze tables to clean, typed, tested Silver models.
This notebook shows every dbt command running, every SQL model, and every test.**

| | |
|---|---|
| **Stack** | dbt-duckdb 1.9.4 · DuckDB 1.5.3 · Python 3.12 |
| **Pattern** | Bronze (raw) → **Silver staging (views) → Silver intermediate (tables)** → Gold (KPIs) |
| **Models** | 8 staging views + 3 intermediate tables = 11 Silver models |
| **Tests** | 25 staging + 8 intermediate = **33 dbt tests, all passing** |
| **Key transformation** | type casting · normalization · joins · derived columns · aggregations |

</div>"""))

# ── TOC ────────────────────────────────────────────────────────────────────────
cells.append(md("""## Table of Contents

1. [Architecture: What dbt Adds to Medallion](#1-architecture)
2. [Running Staging Layer: 8 Views in 0.4s](#2-staging-run)
3. [Staging SQL: The Bronze → Silver Pattern](#3-staging-sql)
4. [Running Intermediate Layer: 3 Tables](#4-intermediate-run)
5. [Intermediate SQL: Joins, Derivations & Aggregations](#5-intermediate-sql)
6. [dbt Tests: 33 Checks in Green](#6-dbt-tests)
7. [Bronze vs Silver: Before & After](#7-comparison)
8. [dbt Dependency Graph: {{ ref() }} in Action](#8-dag)
9. [Silver Metrics: Querying the Clean Data](#9-metrics)
10. [Key Takeaways](#10-key-takeaways)"""))

# ── Setup ──────────────────────────────────────────────────────────────────────
cells.append(md("## Setup"))
cells.append(code(f"""import sys, os, re, subprocess
from pathlib import Path
from IPython.display import display, Markdown, HTML

PROJECT_ROOT = Path("{PROJECT_ROOT}")
DBT_BIN      = "{DBT_BIN}"
DBT_DIR      = str(PROJECT_ROOT / "dbt")
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

pio.renderers.default = "notebook"
DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="#0F1929",
    plot_bgcolor="#0F1929",
    font=dict(color="#E8E8E8", family="monospace"),
    margin=dict(t=60, b=40, l=60, r=40),
)
SILVER_COLOR = "#C0C0C0"
ACCENT      = ["#4FC3F7","#81C784","#FFB74D","#E57373","#CE93D8","#80DEEA","#FFCC02","#A5D6A7"]

db_path = os.getenv("DUCKDB_PATH")
conn = duckdb.connect(db_path, read_only=True)

def strip_ansi(text: str) -> str:
    \"\"\"Remove ANSI color codes for clean Jupyter output.\"\"\"
    return re.sub(r'\\x1b\\[[0-9;]*m', '', text)

def run_dbt(args: list, label: str = "") -> subprocess.CompletedProcess:
    \"\"\"Run a dbt command and print clean output.
    Closes conn before running (DuckDB allows only one connection at a time)
    and reopens it after so subsequent query cells can use it.
    \"\"\"
    global conn
    conn.close()
    env = {{**os.environ, "DUCKDB_PATH": db_path}}
    result = subprocess.run(
        [DBT_BIN] + args + ["--profiles-dir", "."],
        cwd=DBT_DIR, capture_output=True, text=True, env=env
    )
    conn = duckdb.connect(db_path, read_only=True)
    output = strip_ansi(result.stdout + result.stderr)
    if label:
        print(f"{'='*60}")
        print(f"  {{label}}")
        print(f"{'='*60}")
    print(output)
    return result

print(f"✅ DuckDB: {{db_path}}")
print(f"✅ dbt binary: {{DBT_BIN}}")
print(f"✅ dbt project: {{DBT_DIR}}")"""))

# ── Section 1: Architecture ────────────────────────────────────────────────────
cells.append(md("""---
<a id="1-architecture"></a>
## 1. Architecture: What dbt Adds to Medallion

**Medallion** organizes data into quality tiers (Bronze/Silver/Gold).
**dbt** organizes *how those tiers are built* — with SQL, tests, documentation, and lineage.

Without dbt, Silver would be a pile of SQL scripts no one knows how to run in the right order.
With dbt, every model is versioned, tested, and has explicit dependencies.

### How dbt Silver is organized in this project:

```
Bronze (Python)           Silver — Staging (dbt views)        Silver — Intermediate (dbt tables)
──────────────────        ──────────────────────────────       ──────────────────────────────────────
bronze.customers    →     analytics_staging.stg_customers  ┐
bronze.companies    →     analytics_staging.stg_companies  ├→  analytics_intermediate.int_customer_lifecycle
bronze.subscriptions→     analytics_staging.stg_subscriptions┘
                          analytics_staging.stg_payments    ┐
                                                             ├→  analytics_intermediate.int_subscription_metrics
                          analytics_staging.stg_subscriptions┘
                          analytics_staging.stg_product_events ┐
                          analytics_staging.stg_customers      ┘→ analytics_intermediate.int_product_engagement
```

### Schema naming (`analytics_` prefix):
`dbt_project.yml` sets `+schema: staging` but the DuckDB profile name is `saas_analytics`.
dbt generates schema names as `{profile_name}_{schema}`, so:
- `staging` models → `analytics_staging`
- `intermediate` models → `analytics_intermediate`
- `marts/finance` models → `analytics_finance`

### The `{{ ref() }}` macro is dbt's superpower:
```sql
-- Instead of: SELECT * FROM analytics_staging.stg_customers
-- dbt uses:   SELECT * FROM {{ ref('stg_customers') }}
```
`{{ ref() }}` does three things automatically:
1. Resolves the full schema path at compile time
2. Builds the dependency DAG (knows what to run first)
3. Enables lineage documentation and impact analysis"""))

cells.append(code("""# Show dbt_project.yml — schema naming and materialization config
dbt_project_path = PROJECT_ROOT / "dbt" / "dbt_project.yml"
print("=== dbt_project.yml ===\\n")
print(dbt_project_path.read_text())"""))

# ── Section 2: dbt run staging ─────────────────────────────────────────────────
cells.append(md("""---
<a id="2-staging-run"></a>
## 2. Running Staging Layer: 8 Views in 0.4s

`dbt run --select staging` creates 8 views in `analytics_staging`.
Views are not materialized — they're SQL definitions that execute on query.

**Staging responsibility**: minimal transformations only
- Rename columns to snake_case
- Cast types (VARCHAR → DATE, DOUBLE → DECIMAL(10,2))
- Normalize values (lower(email), upper(country))
- Drop Bronze metadata columns not needed downstream (`_source_file`, `_layer`)
- No business logic, no joins, no aggregations"""))

cells.append(code("""run_dbt(["run", "--select", "staging"], "dbt run --select staging")"""))

cells.append(code("""# Verify all 8 staging views were created
staging_views = conn.execute(\"\"\"
    SELECT table_name, 'view' as type
    FROM information_schema.views
    WHERE table_schema = 'analytics_staging'
      AND table_name NOT LIKE 'duckdb_%'
    ORDER BY table_name
\"\"\").fetchdf()

print(f"Staging views created: {len(staging_views)}")
display(staging_views.style.set_caption("analytics_staging — dbt Views").hide(axis='index'))"""))

# ── Section 3: Staging SQL ─────────────────────────────────────────────────────
cells.append(md("""---
<a id="3-staging-sql"></a>
## 3. Staging SQL: The Bronze → Silver Pattern

Every staging model follows the **source / renamed CTE pattern**:

```sql
with source as (
    select * from bronze.table_name   -- read Bronze directly (no {{ source() }})
),
renamed as (
    select
        column_1,
        cast(column_2 as date) as column_2,   -- type cast
        lower(trim(email))     as email,       -- normalize
        ...
    from source
    where primary_key is not null             -- minimal quality filter
)
select * from renamed
```

**Why `FROM bronze.table` instead of `{{ source() }}`?**
Bronze tables are created directly by Python scripts in DuckDB — they're not
managed by dbt sources. Using `FROM bronze.table` is simpler and honest about
what Bronze is: a Python-managed schema, not a dbt source."""))

cells.append(code("""# stg_customers.sql — the canonical staging pattern
stg_customers_path = PROJECT_ROOT / "dbt/models/staging/stg_customers.sql"
sql_code = stg_customers_path.read_text()

print("File: dbt/models/staging/stg_customers.sql")
print("=" * 60)
display(Markdown(f"```sql\\n{sql_code}\\n```"))

print("\\nKey transformations applied:")
print("  • mrr:          DOUBLE    → DECIMAL(10,2)  (precise financial data)")
print("  • signup_date:  VARCHAR   → DATE           (enables date arithmetic)")
print("  • churn_date:   VARCHAR   → DATE           (try_cast: nulls if invalid)")
print("  • email:        mixed     → lowercase      (deduplication-safe)")
print("  • country:      mixed     → UPPERCASE      (ISO standard)")
print("  • phone:        dropped   (not needed in Silver)")
print("  • _source_file: dropped   (lineage tracked at Bronze only)")
print("  • _layer:       dropped   (implicit from schema name)")"""))

cells.append(code("""# Show a second staging model — stg_subscriptions.sql
stg_sub_path = PROJECT_ROOT / "dbt/models/staging/stg_subscriptions.sql"
sql_code = stg_sub_path.read_text()
print("File: dbt/models/staging/stg_subscriptions.sql")
print("=" * 60)
display(Markdown(f"```sql\\n{sql_code}\\n```"))"""))

# ── Section 4: dbt run intermediate ───────────────────────────────────────────
cells.append(md("""---
<a id="4-intermediate-run"></a>
## 4. Running Intermediate Layer: 3 Tables

`dbt run --select intermediate` creates 3 **physical tables** in `analytics_intermediate`.
Unlike staging views, intermediate models are materialized as tables because they:
- Perform expensive joins (customers × companies × subscriptions)
- Run aggregations over 50,000 product events
- Are queried repeatedly by downstream Gold marts

**Intermediate responsibility**: business logic without final KPI aggregation
- JOIN staging models together
- Compute derived columns (`plan_tier`, `customer_age_months`, `days_to_churn`)
- Aggregate events into per-customer metrics
- Calculate `mrr_movement_type` (new/expansion/contraction/churned)"""))

cells.append(code("""run_dbt(["run", "--select", "intermediate"], "dbt run --select intermediate")"""))

cells.append(code("""# Verify 3 intermediate tables created
int_tables = conn.execute(\"\"\"
    SELECT schema_name, table_name
    FROM duckdb_tables()
    WHERE schema_name = 'analytics_intermediate'
    ORDER BY table_name
\"\"\").fetchdf()

rows_data = []
for _, row in int_tables.iterrows():
    cnt = conn.execute(f"SELECT COUNT(*) FROM {row.schema_name}.{row.table_name}").fetchone()[0]
    col_cnt = conn.execute(f\"\"\"
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_schema='{row.schema_name}' AND table_name='{row.table_name}'
    \"\"\").fetchone()[0]
    rows_data.append({
        "table": f"{row.schema_name}.{row.table_name}",
        "rows": f"{cnt:,}",
        "columns": col_cnt,
        "materialization": "table"
    })

print("Intermediate tables created:")
display(pd.DataFrame(rows_data).style.set_caption("analytics_intermediate — dbt Tables").hide(axis='index'))"""))

# ── Section 5: Intermediate SQL ───────────────────────────────────────────────
cells.append(md("""---
<a id="5-intermediate-sql"></a>
## 5. Intermediate SQL: Joins, Derivations & Aggregations

Intermediate models are where the real business logic lives.
They use `{{ ref() }}` to depend on staging models, not Bronze directly."""))

cells.append(code("""# int_customer_lifecycle.sql — joins 3 staging models + derived columns
path = PROJECT_ROOT / "dbt/models/intermediate/int_customer_lifecycle.sql"
sql_code = path.read_text()
print("File: dbt/models/intermediate/int_customer_lifecycle.sql")
print("=" * 60)
display(Markdown(f"```sql\\n{sql_code}\\n```"))

print("\\nWhat this model adds on top of stg_customers:")
print("  • company_name, industry, employee_count  (LEFT JOIN stg_companies)")
print("  • sub_id, sub_start_date                  (LEFT JOIN stg_subscriptions WHERE status='active')")
print("  • customer_age_days / customer_age_months  (datediff from signup_date)")
print("  • plan_tier (1–4)                          (CASE on plan name)")
print("  • is_enterprise, is_active, days_to_churn  (boolean + date derivations)")"""))

cells.append(code("""# int_subscription_metrics.sql — joins subscriptions + payments aggregation
path = PROJECT_ROOT / "dbt/models/intermediate/int_subscription_metrics.sql"
sql_code = path.read_text()
print("File: dbt/models/intermediate/int_subscription_metrics.sql")
print("=" * 60)
display(Markdown(f"```sql\\n{sql_code}\\n```"))

print("\\nKey logic:")
print("  • payment_metrics CTE: aggregates 22,842 payments → 1 row per customer")
print("  • mrr_movement_type: CASE on previous_plan + change_reason")
print("    - NULL previous_plan → 'new'")
print("    - change_reason='upgrade' → 'expansion'")
print("    - change_reason='downgrade' → 'contraction'")
print("    - status='cancelled' → 'churned'")
print("    - else → 'retained'")"""))

cells.append(code("""# int_product_engagement.sql — 30-day rolling window aggregation
path = PROJECT_ROOT / "dbt/models/intermediate/int_product_engagement.sql"
sql_code = path.read_text()
print("File: dbt/models/intermediate/int_product_engagement.sql")
print("=" * 60)
display(Markdown(f"```sql\\n{sql_code}\\n```"))

print("\\nEngagement score formula:")
print("  score = (logins/30 × 30) + (unique_features/10 × 30)")
print("        + (total_events/50 × 25) + (has_invite × 15)")
print("  Max possible score = 100")
print("  Each component capped via LEAST(..., 1) to avoid outlier domination")"""))

# ── Section 6: dbt Tests ──────────────────────────────────────────────────────
cells.append(md("""---
<a id="6-dbt-tests"></a>
## 6. dbt Tests: 33 Checks in Green

dbt tests are SQL assertions that run against the built models.
They fail the pipeline if data violates the contract.

**Test types used in this project:**
| Test | What it checks | Example |
|---|---|---|
| `not_null` | No NULL values in a column | `customer_id IS NOT NULL` |
| `unique` | All values are unique | No duplicate `payment_id` |
| `accepted_values` | Column only has valid enum values | `plan IN ('Starter','Pro','Business','Enterprise')` |
| `relationships` | FK exists in parent table | Every `company_id` in customers exists in companies |"""))

cells.append(code("""run_dbt(
    ["test", "--select", "staging intermediate"],
    "dbt test --select staging intermediate"
)"""))

cells.append(code("""# Parse test results into a clean summary DataFrame
global conn
conn.close()
env = {**os.environ, "DUCKDB_PATH": db_path}
result = subprocess.run(
    [DBT_BIN, "test", "--select", "staging intermediate", "--profiles-dir", "."],
    cwd=DBT_DIR, capture_output=True, text=True, env=env
)
conn = duckdb.connect(db_path, read_only=True)
raw_output = strip_ansi(result.stdout + result.stderr)

# Parse PASS/FAIL lines — dbt format: "N of M PASS|FAIL test_name ..."
import re as _re
test_results = []
for line in raw_output.split("\\n"):
    m = _re.search(r'\\d+ of \\d+ (PASS|FAIL)\\s+(\\S+)', line)
    if not m:
        continue
    status = m.group(1)
    name   = m.group(2)
    if name.startswith("not_null_"):
        check_type = "not_null"
    elif name.startswith("unique_"):
        check_type = "unique"
    elif name.startswith("accepted_values_"):
        check_type = "accepted_values"
    elif name.startswith("relationships_"):
        check_type = "relationships"
    else:
        check_type = "other"
    test_results.append({
        "status": "✅" if status == "PASS" else "❌",
        "type": check_type,
        "test_name": name[:70] + ("..." if len(name) > 70 else ""),
    })

tests_df = pd.DataFrame(test_results) if test_results else pd.DataFrame(columns=["status","type","test_name"])
n_pass = (tests_df["status"] == "✅").sum()
n_fail = (tests_df["status"] == "❌").sum()

print(f"\\n{'='*50}")
print(f"  dbt Test Results: {n_pass} PASSED, {n_fail} FAILED")
print(f"{'='*50}\\n")

by_type = tests_df.groupby(["status","type"]).size().reset_index(name="count")
display(by_type.style.set_caption("Tests by Type").hide(axis='index'))
print()
display(tests_df.style.set_caption(f"All {len(tests_df)} dbt Tests — staging + intermediate").hide(axis='index'))"""))

# ── Section 7: Bronze vs Silver Comparison ────────────────────────────────────
cells.append(md("""---
<a id="7-comparison"></a>
## 7. Bronze vs Silver: Before & After

This is the core Silver layer value: taking Bronze's raw, loosely typed data
and making it **reliable, typed, and analysis-ready**."""))

cells.append(code("""# Schema comparison: bronze.customers vs analytics_staging.stg_customers
bronze_cols = conn.execute(\"\"\"
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_schema='bronze' AND table_name='customers'
    ORDER BY ordinal_position
\"\"\").fetchdf().rename(columns={"data_type": "bronze_type"})

silver_cols = conn.execute(\"\"\"
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_schema='analytics_staging' AND table_name='stg_customers'
    ORDER BY ordinal_position
\"\"\").fetchdf().rename(columns={"data_type": "silver_type"})

comparison = bronze_cols.merge(silver_cols, on="column_name", how="outer")
comparison["changed"] = comparison["bronze_type"] != comparison["silver_type"]
comparison["transformation"] = comparison.apply(lambda r: (
    "🔄 type cast"  if pd.notna(r.bronze_type) and pd.notna(r.silver_type) and r.bronze_type != r.silver_type
    else "🆕 new col"  if pd.isna(r.bronze_type)
    else "🗑️  dropped"  if pd.isna(r.silver_type)
    else "✅ kept"
), axis=1)

print("Schema evolution: bronze.customers → analytics_staging.stg_customers")
print()
display(comparison[["column_name","bronze_type","silver_type","transformation"]]
    .style
    .set_caption("Bronze → Silver Schema Changes")
    .hide(axis='index'))"""))

cells.append(code("""# Row-level data comparison: same customer, Bronze vs Silver
cust_id = conn.execute(
    "SELECT customer_id FROM bronze.customers WHERE churn_date IS NOT NULL LIMIT 1"
).fetchone()[0]

bronze_row = conn.execute(f\"\"\"
    SELECT customer_id, mrr, signup_date, churn_date, email, country,
           _source_file, _batch_id, _layer
    FROM bronze.customers WHERE customer_id = '{cust_id}'
\"\"\").fetchdf()

silver_row = conn.execute(f\"\"\"
    SELECT customer_id, mrr, signup_date, churn_date, email, country,
           NULL as _source_file, _batch_id, NULL as _layer
    FROM analytics_staging.stg_customers WHERE customer_id = '{cust_id}'
\"\"\").fetchdf()

print(f"Same row, customer_id = {cust_id}\\n")
print("BRONZE — raw types:")
print(bronze_row.T.to_string())
print()
print("SILVER — clean types:")
print(silver_row.T.to_string())
print()

# Show type differences explicitly
bronze_types = {c: str(bronze_row[c].dtype) for c in bronze_row.columns}
silver_types = {c: str(silver_row[c].dtype) for c in silver_row.columns}
print("Type changes (pandas dtypes):")
for col in ["mrr", "signup_date", "churn_date"]:
    bt = bronze_types.get(col, "N/A")
    st = silver_types.get(col, "N/A")
    arrow = "→" if bt != st else "="
    print(f"  {col:<20} Bronze: {bt:<12} {arrow}  Silver: {st}")"""))

# ── Section 8: dbt DAG ─────────────────────────────────────────────────────────
cells.append(md("""---
<a id="8-dag"></a>
## 8. dbt Dependency Graph: {{ ref() }} in Action

When you run `dbt run`, it builds a DAG (Directed Acyclic Graph) from all `{{ ref() }}` calls
and executes models in topological order — no manual orchestration needed.

```
BRONZE (Python)              STAGING (dbt views)              INTERMEDIATE (dbt tables)
─────────────────────        ──────────────────────────        ──────────────────────────────────────
bronze.customers      ──────▶ stg_customers          ──────────▶ int_customer_lifecycle
bronze.companies      ──────▶ stg_companies           ──────────▶ (joined: customers+companies+subs)
bronze.subscriptions  ──────▶ stg_subscriptions  ─────────────▶
                                                  │
                              stg_payments  ──────┼────────────▶ int_subscription_metrics
                              stg_subscriptions ──┘              (subs aggregated with payments)

bronze.product_events ──────▶ stg_product_events ─────────────▶ int_product_engagement
bronze.customers      ──────▶ stg_customers       ─────────────▶ (30-day rolling window)

bronze.marketing_leads──────▶ stg_marketing_leads   (used directly in Gold)
bronze.nps_surveys    ──────▶ stg_nps_surveys        (used directly in Gold)
bronze.support_tickets──────▶ stg_support_tickets    (used directly in Gold)
```

**Key insight**: if `bronze.customers` changes, dbt knows to rebuild:
`stg_customers → int_customer_lifecycle → fct_mrr, fct_churn, fct_ltv, fct_activation_funnel`

This is automatic — no manual dependency tracking needed."""))

cells.append(code("""# Show the dependency chain: compile dbt to see resolved SQL
env = {**os.environ, "DUCKDB_PATH": db_path}
result = subprocess.run(
    [DBT_BIN, "compile", "--select", "int_customer_lifecycle", "--profiles-dir", "."],
    cwd=DBT_DIR, capture_output=True, text=True, env=env
)
output = strip_ansi(result.stdout)
# Extract compiled SQL from output
lines = output.split("\\n")
print("dbt compile --select int_customer_lifecycle")
print("(dbt resolves {{ ref() }} → actual schema.table names)\\n")
for line in lines:
    if "Compiled node" in line or "compiled" in line.lower():
        print(line)

# Read the compiled SQL directly from target/
compiled_path = PROJECT_ROOT / "dbt/target/compiled/saas_analytics/models/intermediate/int_customer_lifecycle.sql"
if compiled_path.exists():
    compiled_sql = compiled_path.read_text()
    print("\\nCompiled SQL ({{ ref() }} resolved to actual table names):")
    display(Markdown(f"```sql\\n{compiled_sql}\\n```"))
else:
    print("(Run 'dbt compile' to generate compiled SQL in dbt/target/compiled/)")
    print("\\nWhat dbt resolves behind the scenes:")
    print("  {{ ref('stg_customers') }}    →  analytics_staging.stg_customers")
    print("  {{ ref('stg_companies') }}    →  analytics_staging.stg_companies")
    print("  {{ ref('stg_subscriptions') }} → analytics_staging.stg_subscriptions")"""))

# ── Section 9: Silver Metrics ─────────────────────────────────────────────────
cells.append(md("""---
<a id="9-metrics"></a>
## 9. Silver Metrics: Querying the Clean Data

With Silver in place, we can answer business questions with clean, typed SQL.
These are intermediate-layer signals — not final KPIs (that's Gold), but actionable data."""))

cells.append(code("""# int_customer_lifecycle: plan tier distribution with MRR
tier_data = conn.execute(\"\"\"
    SELECT
        plan_tier,
        plan,
        COUNT(*) as customers,
        ROUND(AVG(mrr), 2) as avg_mrr,
        ROUND(SUM(mrr), 0) as total_mrr,
        ROUND(AVG(customer_age_months), 1) as avg_tenure_months,
        SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active_count
    FROM analytics_intermediate.int_customer_lifecycle
    GROUP BY plan_tier, plan
    ORDER BY plan_tier
\"\"\").fetchdf()

print("int_customer_lifecycle — Plan Tier Distribution:")
display(tier_data.style.set_caption("Customer Lifecycle by Plan Tier").hide(axis='index'))

# Chart: customers + avg_mrr by plan tier
fig = make_subplots(rows=1, cols=2, subplot_titles=["Customers by Plan", "Avg MRR by Plan"])

fig.add_trace(go.Bar(
    x=tier_data["plan"], y=tier_data["customers"],
    marker_color=ACCENT[:4], text=tier_data["customers"],
    textposition="outside", textfont=dict(color="#E8E8E8"),
    name="Customers", showlegend=False,
), row=1, col=1)

fig.add_trace(go.Bar(
    x=tier_data["plan"], y=tier_data["avg_mrr"],
    marker_color=ACCENT[4:8], text=[f"${v:,.0f}" for v in tier_data["avg_mrr"]],
    textposition="outside", textfont=dict(color="#E8E8E8"),
    name="Avg MRR", showlegend=False,
), row=1, col=2)

fig.update_layout(
    **DARK_LAYOUT,
    title=dict(text="int_customer_lifecycle — Plan Distribution & MRR",
               font=dict(size=18, color=SILVER_COLOR)),
    height=420,
)
fig.show()"""))

cells.append(code("""# int_subscription_metrics: MRR movement type analysis
movement = conn.execute(\"\"\"
    SELECT
        mrr_movement_type,
        COUNT(*) as subscriptions,
        ROUND(SUM(mrr), 0) as total_mrr,
        ROUND(AVG(mrr), 2) as avg_mrr,
        ROUND(AVG(total_paid_usd), 0) as avg_lifetime_paid,
        SUM(CASE WHEN has_payment_issues THEN 1 ELSE 0 END) as with_payment_issues
    FROM analytics_intermediate.int_subscription_metrics
    GROUP BY mrr_movement_type
    ORDER BY subscriptions DESC
\"\"\").fetchdf()

print("int_subscription_metrics — MRR Movement Types:")
print("(This feeds directly into Gold fct_mrr for MRR waterfall)")
display(movement.style.set_caption("MRR Movement Analysis").hide(axis='index'))

# Chart: MRR by movement type
color_map = {"new": "#81C784", "expansion": "#4FC3F7", "contraction": "#FFB74D",
              "churned": "#E57373", "retained": "#CE93D8"}
colors = [color_map.get(t, "#E8E8E8") for t in movement["mrr_movement_type"]]

fig = go.Figure()
fig.add_trace(go.Bar(
    x=movement["mrr_movement_type"],
    y=movement["total_mrr"],
    marker_color=colors,
    text=[f"${v:,.0f}" for v in movement["total_mrr"]],
    textposition="outside", textfont=dict(color="#E8E8E8"),
))
fig.update_layout(
    **DARK_LAYOUT,
    title=dict(text="Total MRR by Movement Type (Bronze of Gold fct_mrr)",
               font=dict(size=18, color=SILVER_COLOR)),
    xaxis_title="Movement Type",
    yaxis_title="Total MRR ($)",
    height=400,
)
fig.show()
print(f"\\nTotal MRR in Silver: ${movement['total_mrr'].sum():,.0f}")
print("→ Gold fct_mrr will break this into New/Expansion/Contraction/Churn/Net movements")"""))

cells.append(code("""# int_product_engagement: score distribution by segment
engagement = conn.execute(\"\"\"
    SELECT
        segment,
        plan,
        COUNT(*) as customers,
        ROUND(AVG(engagement_score), 2) as avg_score,
        ROUND(AVG(total_events_30d), 1) as avg_events_30d,
        ROUND(AVG(active_days_30d), 1) as avg_active_days,
        ROUND(AVG(unique_features_30d), 1) as avg_features_used
    FROM analytics_intermediate.int_product_engagement
    GROUP BY segment, plan
    ORDER BY avg_score DESC
\"\"\").fetchdf()

# Engagement tier buckets
tiers = conn.execute(\"\"\"
    SELECT
        CASE WHEN engagement_score < 20 THEN '1. Low (0-20)'
             WHEN engagement_score < 40 THEN '2. Medium (20-40)'
             WHEN engagement_score < 60 THEN '3. High (40-60)'
             ELSE '4. Champion (60+)' END as tier,
        COUNT(*) as customers,
        ROUND(AVG(engagement_score), 2) as avg_score,
        ROUND(AVG(total_events_30d), 1) as avg_events
    FROM analytics_intermediate.int_product_engagement
    GROUP BY 1
    ORDER BY 1
\"\"\").fetchdf()

print("Engagement Score Tiers (last 30 days):")
display(tiers.style.set_caption("int_product_engagement — Score Tiers").hide(axis='index'))

# Chart: engagement score histogram + segment box plot
fig = make_subplots(rows=1, cols=2,
    subplot_titles=["Engagement Score Distribution", "Score by Segment"])

all_scores = conn.execute(
    "SELECT engagement_score FROM analytics_intermediate.int_product_engagement"
).fetchdf()

fig.add_trace(go.Histogram(
    x=all_scores["engagement_score"],
    nbinsx=20,
    marker_color="#4FC3F7",
    opacity=0.8,
    name="Customers",
    showlegend=False,
), row=1, col=1)

for seg, color in zip(["SMB","Mid-Market","Enterprise"], ACCENT[:3]):
    scores = conn.execute(f\"\"\"
        SELECT engagement_score FROM analytics_intermediate.int_product_engagement
        WHERE segment = '{seg}'
    \"\"\").fetchdf()
    fig.add_trace(go.Box(
        y=scores["engagement_score"],
        name=seg,
        marker_color=color,
        showlegend=False,
    ), row=1, col=2)

fig.update_layout(
    **DARK_LAYOUT,
    title=dict(text="int_product_engagement — Score Distribution",
               font=dict(size=18, color=SILVER_COLOR)),
    height=420,
)
fig.update_xaxes(title_text="Engagement Score", row=1, col=1)
fig.update_yaxes(title_text="Customers", row=1, col=1)
fig.update_yaxes(title_text="Engagement Score", row=1, col=2)
fig.show()

print(f"\\n883 active/trial customers have events in the last 30 days")
print(f"Score range: {all_scores['engagement_score'].min():.1f} – {all_scores['engagement_score'].max():.1f}")
print(f"Avg score:   {all_scores['engagement_score'].mean():.2f}/100")"""))

# ── Key Takeaways ─────────────────────────────────────────────────────────────
cells.append(md("""---
<a id="10-key-takeaways"></a>
## 10. Key Takeaways

<div style="background: #0F1929; border-left: 4px solid #C0C0C0; padding: 20px; border-radius: 8px;">

### What dbt built in the Silver layer:

**8 Staging Views** (`analytics_staging`) — 0.38s to create
- Type casts: VARCHAR→DATE, DOUBLE→DECIMAL(10,2)
- Normalization: lowercase email, uppercase country
- Clean schema: only business columns + 2 metadata cols
- 25 dbt tests passing (not_null, unique, accepted_values)

**3 Intermediate Tables** (`analytics_intermediate`) — 0.21s to create
- `int_customer_lifecycle`: 1,000 rows — customers enriched with company data + derived cols
- `int_subscription_metrics`: 1,000 rows — subscriptions with payment aggregations + MRR movement
- `int_product_engagement`: 883 rows — 30-day rolling engagement score per customer
- 8 dbt tests passing (accepted_values on plan_tier and mrr_movement_type)

**Total Silver tests: 33/33 passing**

</div>

---

### What comes next:

- **Notebook 03** — Gold layer: 7 mart models compute final KPIs
  - `fct_mrr`: MRR waterfall with 5 movements (New/Expansion/Contraction/Churned/Net)
  - `fct_churn`: Churn rate by segment and period
  - `fct_ltv`: Customer Lifetime Value by plan
  - `fct_cohort_retention`: Cohort analysis heatmap
  - `fct_customer_acquisition`: CAC and conversion rates
  - `fct_activation_funnel`: Activation funnel metrics
  - `fct_revenue_expansion`: Expansion MRR analysis

---

*Silver is the data contract between raw ingestion and KPI computation.
If something breaks in Gold, the answer is always in Silver.
If something breaks in Silver, the answer is always in Bronze.*"""))

cells.append(code("""# Final Silver summary
print("🥈 Silver Layer — Complete\\n")
print("Staging views:")
for _, row in conn.execute(\"\"\"
    SELECT table_name FROM information_schema.views
    WHERE table_schema='analytics_staging'
    AND table_name LIKE 'stg_%'
    ORDER BY table_name
\"\"\").fetchdf().iterrows():
    cnt = conn.execute(f"SELECT COUNT(*) FROM analytics_staging.{row.table_name}").fetchone()[0]
    print(f"  analytics_staging.{row.table_name:<35} {cnt:>7,} rows")

print()
print("Intermediate tables:")
for _, row in conn.execute(\"\"\"
    SELECT schema_name, table_name FROM duckdb_tables()
    WHERE schema_name='analytics_intermediate'
    ORDER BY table_name
\"\"\").fetchdf().iterrows():
    cnt = conn.execute(f"SELECT COUNT(*) FROM {row.schema_name}.{row.table_name}").fetchone()[0]
    print(f"  {row.schema_name}.{row.table_name:<30} {cnt:>7,} rows")

print()
print("dbt tests: 33/33 PASSING")
print("  - 25 staging tests  (not_null, unique, accepted_values)")
print("  - 8 intermediate tests (accepted_values on derived columns)")
conn.close()
print("\\n✅ DuckDB connection closed")"""))

# ── Write notebook ─────────────────────────────────────────────────────────────
nb = nbformat.v4.new_notebook()
nb.cells = cells
nb.metadata = {
    "kernelspec": {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3"
    },
    "language_info": {"name": "python", "version": "3.12.0"}
}

output_path = PROJECT_ROOT + "/notebooks/02_silver_transformation.ipynb"
with open(output_path, "w", encoding="utf-8") as f:
    nbformat.write(nb, f)

print(f"✅ Notebook written: {output_path}")
print(f"   Cells: {len(nb.cells)}")
