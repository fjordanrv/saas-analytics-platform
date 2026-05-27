# Contexto de Continuidad — SaaS Analytics Platform

## Estilo de trabajo acordado
- Trabajamos paso a paso, nunca saltando pasos
- Antes de codificar siempre explicamos el concepto
- El usuario pregunta hasta entender completamente
- Claude explica con analogías simples y ejemplos concretos
- Design First Then Build — diseñamos antes de codificar
- Claude Code ejecuta, Claude chat explica y diseña
- Auto mode solo para tareas con múltiples archivos simples

## Decisiones de arquitectura y por qué

### ¿Por qué Medallion (Bronze/Silver/Gold)?
Bronze = dato crudo sin modificar (trazabilidad)
Silver = limpieza y enriquecimiento (dbt staging + intermediate)
Gold = KPIs finales (dbt marts)
Permite volver a Bronze si algo sale mal en capas superiores.

### ¿Por qué dbt además de Medallion?
Medallion organiza el dato. dbt organiza cómo se construye.
Sin dbt el SQL es código suelto sin tests ni dependencias.
Con dbt: versionado, testeable, documentado, con linaje visual.

### ¿Por qué DuckDB en desarrollo?
Motor SQL local sin servidor. Mismo SQL que Databricks.
Cambiar a producción = solo cambiar DB_TYPE en .env.
Cero fricción para aprender sin necesitar cuentas cloud.

### ¿Por qué Airflow con Astro CLI?
Estándar en empresas SaaS y Fintech.
Astro CLI replica producción localmente con Docker.
Mismo código corre local y en Astronomer cloud.

### ¿Por qué separar staging/intermediate/marts en dbt?
staging = limpieza mínima, sin business logic
intermediate = joins y cálculos derivados
marts = KPIs finales por dominio de negocio
Separación de responsabilidades, fácil de mantener.

### ¿Por qué Singleton en DatabaseConnection?
Una sola conexión a DuckDB en todo el pipeline.
Evita conflictos de escritura simultánea.
Fácil de cambiar de DuckDB a Databricks sin tocar otros scripts.

### ¿Por qué clases en ingestion y quality?
Estado compartido entre métodos (self.checks, self.conn).
Method chaining en DataQualityChecker.
Más limpio que pasar variables entre funciones.

### ¿Por qué Faker para datos mock?
Genera datos ficticios pero realistas para SaaS B2B.
Distribuciones reales: 40% US, 3% churn, 60% SMB.
Con seed(42) los datos son reproducibles.

### ¿Por qué Loguru en lugar de logging nativo?
Módulo centralizado get_logger() — un solo punto de config.
Colores en terminal, rotación automática de archivos.
Más legible para aprender y para producción.

## Lo que el usuario aprendió en esta conversación

### Conceptos de arquitectura
- Medallion Architecture Bronze/Silver/Gold
- Por qué dbt y Medallion se complementan
- Materialización en dbt: view vs table vs incremental
- {{ ref() }} construye el DAG de dependencias en dbt
- CTEs con source/renamed — separación de responsabilidades

### Python avanzado
- Patrón Singleton — una sola instancia compartida
- Method chaining — return self para encadenar métodos
- self vs cls — instancia vs clase
- @dataclass — genera __init__ automáticamente
- @classmethod — método pertenece a la clase
- Variables globales vs closures vs clases
- Type hints y from __future__ import annotations
- os.getenv + python-dotenv — cargar .env en memoria

### Data Engineering
- Data Quality Checks programáticos con severidad
- Bronze ingesta sin modificar + metadata de trazabilidad
- dbt tests: not_null, unique, accepted_values, relationships
- Airflow DAG — tareas, dependencias, paralelismo
- Docker volúmenes — no duplican, comparten disco
- Astro CLI — replica producción localmente

### KPIs SaaS definidos (6 dominios, 17 KPIs)
Ver docs/kpi_definitions.md para detalle completo.
- Revenue: MRR (5 movimientos), ARR, NRR
- Retention: Churn Rate, Logo vs Revenue, Cohort
- Growth: Activation Rate, Conversion Rate, CAC
- Product: DAU/MAU/Stickiness, Feature Adoption, Engagement
- Customer Success: NPS, Health Score, TTR, At Risk
- LTV: LTV, LTV/CAC, Payback Period

### Herramientas y cuándo usar cada una
Claude chat    → diseño, decisiones, explicaciones
Claude Code    → ejecución, creación de archivos
NotebookLM     → infografías y diseño visual
Auto mode      → solo para tareas con múltiples archivos

## Estado del proyecto al cerrar esta sesión

### Completado
- Bronze: 8 tablas, 79,342 filas, 100% quality score
- dbt staging: 8 modelos (vistas), 25 tests
- dbt intermediate: 3 modelos (tablas), 8 tests
- dbt marts Gold: 7 modelos (tablas), 21 tests
- 54 dbt tests pasando en total
- Airflow configurado con Astro CLI y Docker
- dag_full_pipeline.py con 11 tareas
- Volumen Docker montado correctamente
- logger.py detecta Docker vs local automáticamente

### Pendiente al retomar
1. Verificar que el DAG corre completo sin errores en Airflow
2. Capturar screenshots de Airflow UI para LinkedIn
3. 4 notebooks Jupyter con análisis exploratorio
4. README.md profesional con diagramas Mermaid
5. Crear cuenta GitHub y hacer push
6. Crear cuenta Databricks Community Edition
7. Migrar de DuckDB a Databricks (solo cambiar .env)
8. Dashboards en Figma/Canva con los KPIs
