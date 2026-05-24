# KPI Definitions — CloudMetrics Inc.

Seis dominios de KPIs que cubren la salud completa del negocio SaaS.
Todos los KPIs se calculan en la capa Gold de dbt y se actualizan diariamente vía Airflow.

---

## 1. Revenue

Mide los ingresos recurrentes y su evolución mes a mes.
Owner: **Finance / RevOps**

### MRR (Monthly Recurring Revenue)

**Definición:** Ingresos recurrentes mensuales totales. Se descompone en cinco movimientos para entender de dónde viene y a dónde va cada mes.

| Componente | Fórmula | Descripción |
|---|---|---|
| **New MRR** | `SUM(mrr)` de clientes nuevos en el mes | Ingresos de clientes que se suscriben por primera vez |
| **Expansion MRR** | `SUM(mrr_nuevo - mrr_anterior)` donde > 0 | Ingresos adicionales por upgrades de plan |
| **Contraction MRR** | `SUM(mrr_anterior - mrr_nuevo)` donde > 0 | Pérdida parcial de ingresos por downgrades |
| **Churned MRR** | `SUM(mrr)` de clientes que cancelaron en el mes | Ingresos perdidos por cancelaciones |
| **Net New MRR** | `New + Expansion - Contraction - Churned` | Crecimiento neto de MRR en el mes |

**Granularidad:** mensual, por plan, por segmento.
**Benchmark:** Net New MRR positivo → crecimiento; negativo → contracción.

---

### ARR (Annual Recurring Revenue)

**Definición:** Proyección anualizada del MRR actual.

```
ARR = MRR × 12
```

**Granularidad:** mensual (snapshot al cierre del mes).
**Benchmark:** crecimiento ARR YoY > 100% en early-stage, > 30% en growth-stage.

---

### NRR (Net Revenue Retention)

**Definición:** Porcentaje de MRR retenido de la cohorte de clientes existentes al inicio del período, incluyendo expansión y contracción. No incluye New MRR.

```
NRR = (MRR_inicio + Expansion - Contraction - Churned) / MRR_inicio × 100
```

**Granularidad:** mensual, por cohorte de signup.
**Benchmark industria:**
- < 100%: el negocio encoge sin nuevos clientes (malo)
- 100-110%: saludable
- > 120%: best-in-class (Snowflake, Datadog nivel)

---

## 2. Retention

Mide la capacidad del producto de retener clientes y revenue.
Owner: **Customer Success**

### Churn Rate

**Definición:** Porcentaje de clientes activos al inicio del período que cancelaron su suscripción.

```
Churn Rate = (Clientes que cancelaron en el mes / Clientes activos al inicio del mes) × 100
```

**Granularidad:** mensual, por segmento, por plan.
**Benchmark industria:**
- SMB: 3-7% mensual (aceptable < 5%)
- Enterprise: 0.5-2% mensual (aceptable < 1%)

---

### Logo Churn vs Revenue Churn

| Métrica | Fórmula | Qué mide |
|---|---|---|
| **Logo Churn** | `Clientes cancelados / Clientes inicio × 100` | Número de cuentas perdidas |
| **Revenue Churn** | `MRR cancelado / MRR inicio × 100` | Valor perdido por cancelaciones |

> Si Revenue Churn < Logo Churn: los clientes que se van son los pequeños (positivo).
> Si Revenue Churn > Logo Churn: los clientes que se van son los grandes (señal de alarma).

**Granularidad:** mensual.

---

### Cohort Retention

**Definición:** Porcentaje de clientes de una cohorte de signup que siguen activos N meses después.

```
Cohort Retention (mes N) = Clientes activos en mes N / Clientes iniciales de la cohorte × 100
```

**Granularidad:** cohorte mensual × mes de vida (0, 1, 3, 6, 12 meses).
**Benchmark:** retención mes 12 > 60% es saludable en SaaS B2B.

---

## 3. Growth

Mide la adquisición y conversión de nuevos clientes.
Owner: **Sales / Marketing**

### New Customers

**Definición:** Número de clientes que se activaron por primera vez en el período.

```
New Customers = COUNT(customer_id) WHERE signup_date IN período
```

**Granularidad:** diaria, semanal, mensual. Por canal, por segmento.

---

### Activation Rate

**Definición:** Porcentaje de nuevos clientes que completan los 3 pasos de activación en los primeros 14 días desde el signup.

**Los 3 pasos de activación:**
1. **Login** — primer inicio de sesión completado
2. **Feature Use** — uso de al menos una feature del producto
3. **Invite** — invitación enviada a al menos un colaborador

```
Activation Rate = (Clientes que completaron los 3 pasos en 14 días / Total nuevos clientes) × 100
```

**Granularidad:** por cohorte semanal de signup.
**Benchmark:** > 40% es saludable; > 60% es excelente.

---

### Conversion Rate

**Definición:** Porcentaje de leads de marketing que se convierten en clientes de pago.

```
Conversion Rate = (Leads convertidos / Total leads) × 100
```

**Granularidad:** mensual, por canal, por campaña.
**Benchmark:** 2-5% lead-to-customer es típico en SaaS B2B.

---

### CAC (Customer Acquisition Cost)

**Definición:** Costo promedio de adquirir un nuevo cliente por canal de marketing.

```
CAC = Total gasto en marketing del canal / Número de clientes adquiridos por ese canal
```

**Granularidad:** mensual, por canal.
**Benchmark por canal:** ver `docs/data_sources.md` — sección Marketing.

---

## 4. Product

Mide el engagement y adopción del producto.
Owner: **Product**

### DAU / MAU / Stickiness

| Métrica | Fórmula | Descripción |
|---|---|---|
| **DAU** | `COUNT(DISTINCT customer_id)` con evento en el día | Usuarios activos diarios |
| **MAU** | `COUNT(DISTINCT customer_id)` con evento en el mes | Usuarios activos mensuales |
| **Stickiness** | `(DAU / MAU) × días del mes calendario` | Frecuencia de uso relativa al mes |

> Stickiness > 50% indica que los usuarios vuelven más de la mitad de los días disponibles.

**Granularidad:** DAU/MAU diario; Stickiness mensual.
**Benchmark:** Stickiness > 20% es aceptable; > 40% es excelente en SaaS B2B.

---

### Feature Adoption Rate

**Definición:** Porcentaje de usuarios activos que usan una feature específica en el mes.

```
Feature Adoption Rate = (MAU que usaron la feature / MAU total) × 100
```

**Granularidad:** mensual, por feature (`feature_name` en `product_events`).

---

### Engagement Score (0-100)

**Definición:** Score compuesto que mide la profundidad de uso del producto por cliente.

```
Engagement Score = (Frecuencia × 0.30)
                 + (Variedad × 0.30)
                 + (Profundidad × 0.25)
                 + (Colaboración × 0.15)
```

| Componente | Peso | Medición |
|---|---|---|
| **Frecuencia** | 30% | Días activos en el mes / días del mes |
| **Variedad** | 30% | Número de `event_type` distintos usados / total tipos |
| **Profundidad** | 25% | Número de `feature_name` distintas / total features |
| **Colaboración** | 15% | Eventos de tipo `invite` en el mes (normalizado) |

**Granularidad:** mensual por cliente; agrupable por segmento, plan, país.

---

## 5. Customer Success

Mide la salud y satisfacción de la base de clientes.
Owner: **Customer Success**

### NPS (Net Promoter Score)

**Definición:** Mide la probabilidad de que un cliente recomiende el producto. Siempre se reporta junto al `response_rate_pct` para contextualizar la representatividad.

```
NPS = %Promoters - %Detractors

response_rate_pct = (Respuestas recibidas / Encuestas enviadas) × 100
```

| Categoría | Score | % en fórmula |
|---|---|---|
| Promoter | 9-10 | Se suma |
| Passive | 7-8 | Se ignora |
| Detractor | 0-6 | Se resta |

**Rango:** -100 a +100.
**Granularidad:** trimestral por cohorte; mensual a nivel agregado.
**Benchmark:** > 0 aceptable; > 30 bueno; > 50 excelente.

---

### Health Score (0-100)

**Definición:** Score compuesto que predice el riesgo de churn de un cliente. Ver fórmula completa en `docs/data_sources.md` — sección Customer Success.

```
Health Score = (NPS norm. × 0.30) + (Engagement × 0.30) + (Pagos × 0.25) + (Tickets × 0.15)
```

**Granularidad:** semanal por cliente.
**Umbrales:**
- ≥ 70: cliente saludable
- 40 – 69: cliente en riesgo, intervención recomendada
- < 40: cliente en riesgo crítico (**at-risk**)

---

### TTR (Time to Resolution)

**Definición:** Tiempo promedio desde la apertura hasta la resolución de un ticket de soporte.

```
TTR = AVG(resolved_at - created_at) por prioridad
```

**Granularidad:** semanal, por prioridad (`low`, `medium`, `high`, `critical`).
**SLA objetivo:**

| Prioridad | TTR objetivo |
|---|---|
| `critical` | < 4 horas |
| `high` | < 24 horas |
| `medium` | < 72 horas |
| `low` | < 7 días |

---

### Customers at Risk

**Definición:** Clientes activos con Health Score < 40. Requieren intervención inmediata de CS.

```
Customers at Risk = COUNT(customer_id) WHERE health_score < 40 AND status = 'active'
```

**Granularidad:** diario.

---

## 6. LTV (Lifetime Value)

Mide el valor económico total esperado de un cliente durante su vida útil.
Owner: **Finance / RevOps**

### LTV

**Definición:** Valor total esperado de un cliente, calculado como el ARPU dividido por la tasa de churn mensual.

```
LTV = ARPU / Churn Rate mensual

ARPU = MRR total / Clientes activos
```

**Granularidad:** mensual total; por segmento (`startup`, `smb`, `enterprise`); por plan.
**Nota:** usar Churn Rate en decimal (e.g., 0.03 para 3%).

---

### LTV por Segmento

**Definición:** LTV calculado de forma independiente para cada segmento de cliente.

```
LTV_segmento = ARPU_segmento / Churn_Rate_segmento
```

**Granularidad:** mensual por segmento.

---

### LTV/CAC Ratio

**Definición:** Relación entre el valor de vida del cliente y el costo de adquirirlo. Principal indicador de eficiencia económica del negocio.

```
LTV/CAC = LTV / CAC
```

**Granularidad:** mensual por canal de adquisición.
**Benchmark industria:**
- < 1: el negocio destruye valor (insostenible)
- 1-3: márgenes ajustados, necesita optimización
- > 3: negocio saludable y escalable ✓
- > 5: muy eficiente (potencial subinversión en adquisición)

---

### Payback Period

**Definición:** Meses necesarios para recuperar el CAC a partir del ARPU generado por el cliente.

```
Payback Period = CAC / ARPU  (en meses)
```

**Granularidad:** mensual, por canal, por segmento.
**Benchmark industria:**
- < 12 meses: excelente
- 12-18 meses: aceptable
- > 24 meses: preocupante (flujo de caja comprometido)
