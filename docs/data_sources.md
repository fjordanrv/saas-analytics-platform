
# Data Sources — CloudMetrics Inc.

Cinco fuentes de datos que alimentan el pipeline Bronze → Silver → Gold.
Todas las tablas aterrizan en la capa Bronze de DuckDB como raw + metadata de ingesta.

---

## 1. CRM

Gestiona la base de clientes y empresas. Modelo Account-Contact: una empresa (`companies`) puede tener múltiples contactos (`customers`).

### `customers`

| Campo | Tipo | Descripción |
|---|---|---|
| `customer_id` | VARCHAR (PK) | Identificador único del cliente |
| `company_id` | VARCHAR (FK) | Empresa a la que pertenece |
| `full_name` | VARCHAR | Nombre completo del contacto |
| `email` | VARCHAR | Email corporativo (único) |
| `phone` | VARCHAR | Teléfono de contacto |
| `country` | VARCHAR | País del cliente |
| `segment` | VARCHAR | Segmento: `startup`, `smb`, `enterprise` |
| `plan` | VARCHAR | Plan activo: `starter`, `growth`, `enterprise` |
| `mrr` | DECIMAL(10,2) | MRR mensual en USD |
| `signup_date` | DATE | Fecha de registro |
| `status` | VARCHAR | Estado: `active`, `churned`, `trial` |
| `churn_date` | DATE | Fecha de baja (NULL si activo) |
| `activation_completed` | BOOLEAN | Si completó los 3 pasos de activación |
| `is_b2b` | BOOLEAN | True si es cliente B2B |

### `companies`

| Campo | Tipo | Descripción |
|---|---|---|
| `company_id` | VARCHAR (PK) | Identificador único de la empresa |
| `name` | VARCHAR | Nombre de la empresa |
| `industry` | VARCHAR | Industria: `tech`, `finance`, `retail`, `health`, etc. |
| `employee_count` | INTEGER | Número de empleados |
| `country` | VARCHAR | País de la empresa |
| `account_manager` | VARCHAR | Nombre del account manager asignado |

---

## 2. Product Events

Eventos de comportamiento del producto. Una sola tabla de eventos con sesiones definidas por inactividad.

**Definición de sesión:** ventana de 30 minutos de inactividad — si pasan más de 30 min entre eventos del mismo `customer_id`, se abre un nuevo `session_id`.

### `product_events`

| Campo | Tipo | Descripción |
|---|---|---|
| `event_id` | VARCHAR (PK) | Identificador único del evento |
| `customer_id` | VARCHAR (FK) | Cliente que generó el evento |
| `session_id` | VARCHAR | Sesión de 30 min de inactividad |
| `event_type` | VARCHAR | Tipo de evento (ver distribución abajo) |
| `feature_name` | VARCHAR | Feature específica usada (si aplica) |
| `timestamp` | TIMESTAMP | Momento exacto del evento (UTC) |
| `device` | VARCHAR | Dispositivo: `web`, `mobile`, `api` |
| `country` | VARCHAR | País desde donde se generó el evento |

### Distribución de `event_type`

| Tipo | Proporción | Descripción |
|---|---|---|
| `login` | 35% | Inicio de sesión |
| `feature_use` | 30% | Uso de una feature del producto |
| `export` | 10% | Exportación de datos o reportes |
| `api_call` | 10% | Llamada vía API |
| `invite` | 8% | Invitación a un colaborador |
| `settings` | 5% | Cambio de configuración |
| `billing` | 2% | Acción relacionada con facturación |

---

## 3. Billing

Gestiona suscripciones y pagos. Los upgrades/downgrades se modelan como cierre de suscripción vieja + apertura de suscripción nueva (Opción A — event-based).

### `subscriptions`

| Campo | Tipo | Descripción |
|---|---|---|
| `sub_id` | VARCHAR (PK) | Identificador único de suscripción |
| `customer_id` | VARCHAR (FK) | Cliente titular |
| `company_id` | VARCHAR (FK) | Empresa asociada |
| `plan` | VARCHAR | Plan: `starter`, `growth`, `enterprise` |
| `mrr` | DECIMAL(10,2) | MRR de esta suscripción en USD |
| `start_date` | DATE | Inicio de vigencia |
| `end_date` | DATE | Fin de vigencia (NULL si activa) |
| `status` | VARCHAR | Estado: `active`, `cancelled`, `upgraded`, `downgraded` |
| `previous_plan` | VARCHAR | Plan anterior (NULL si es primera suscripción) |
| `change_reason` | VARCHAR | Motivo del cambio: `upgrade`, `downgrade`, `churn`, `trial_end` |

### `payments`

| Campo | Tipo | Descripción |
|---|---|---|
| `payment_id` | VARCHAR (PK) | Identificador único del pago |
| `sub_id` | VARCHAR (FK) | Suscripción asociada |
| `customer_id` | VARCHAR (FK) | Cliente pagador |
| `amount` | DECIMAL(10,2) | Monto cobrado en USD |
| `payment_date` | DATE | Fecha del intento de pago |
| `status` | VARCHAR | Estado: `success`, `failed`, `refunded` |
| `payment_method` | VARCHAR | Método: `card`, `bank_transfer`, `paypal` |
| `attempt_number` | INTEGER | Número de intento (1 = primer cobro, 2+ = reintento) |

> **Nota modelado:** cada fila es un intento de cobro. Un pago fallido con reintento exitoso genera 2 filas con el mismo `sub_id` y distinto `attempt_number`.

---

## 4. Marketing

Leads generados por campañas de marketing. Atribución por **last touch** — se asigna todo el crédito al último canal antes de la conversión.

### `marketing_leads`

| Campo | Tipo | Descripción |
|---|---|---|
| `lead_id` | VARCHAR (PK) | Identificador único del lead |
| `email` | VARCHAR | Email del lead |
| `source` | VARCHAR | Fuente: `google`, `linkedin`, `blog`, `referral`, etc. |
| `campaign` | VARCHAR | Nombre de la campaña |
| `channel` | VARCHAR | Canal de adquisición (ver CAC abajo) |
| `lead_date` | DATE | Fecha de captación del lead |
| `conversion_date` | DATE | Fecha de conversión a cliente (NULL si no convirtió) |
| `converted` | BOOLEAN | True si el lead se convirtió en cliente |
| `cac_usd` | DECIMAL(10,2) | Costo de adquisición en USD |

### CAC estimado por canal

| Canal | Rango CAC (USD) | Notas |
|---|---|---|
| `organic` | $0 | SEO, directo — sin coste pagado |
| `paid_search` | $180 – $350 | Google Ads, Bing Ads |
| `referral` | $50 – $120 | Programa de referidos |
| `email` | $30 – $80 | Email marketing propio |
| `social` | $90 – $200 | LinkedIn Ads, Twitter/X Ads |

---

## 5. Customer Success

Encuestas NPS, tickets de soporte y health score por cliente.

### `nps_surveys`

| Campo | Tipo | Descripción |
|---|---|---|
| `nps_id` | VARCHAR (PK) | Identificador único de la encuesta |
| `customer_id` | VARCHAR (FK) | Cliente encuestado |
| `score` | INTEGER | Puntuación 0-10 |
| `category` | VARCHAR | Categoría según score (ver abajo) |
| `survey_date` | DATE | Fecha de respuesta |
| `comment` | TEXT | Comentario abierto (opcional) |
| `health_score` | DECIMAL(5,2) | Health score calculado del cliente (0-100) |

**Categorías NPS:**

| Categoría | Rango de score |
|---|---|
| `detractor` | 0 – 6 |
| `passive` | 7 – 8 |
| `promoter` | 9 – 10 |

### `tickets`

| Campo | Tipo | Descripción |
|---|---|---|
| `ticket_id` | VARCHAR (PK) | Identificador único del ticket |
| `customer_id` | VARCHAR (FK) | Cliente que abrió el ticket |
| `type` | VARCHAR | Tipo: `bug`, `feature_request`, `billing`, `onboarding` |
| `priority` | VARCHAR | Prioridad: `low`, `medium`, `high`, `critical` |
| `status` | VARCHAR | Estado: `open`, `in_progress`, `resolved`, `closed` |
| `created_at` | TIMESTAMP | Fecha y hora de apertura |
| `resolved_at` | TIMESTAMP | Fecha y hora de resolución (NULL si abierto) |
| `satisfaction` | INTEGER | CSAT post-resolución: 1-5 (NULL si no respondió) |

### Fórmula Health Score (0-100)

```
Health Score = (NPS normalizado × 0.30)
             + (Engagement Score × 0.30)
             + (Historial de pagos × 0.25)
             + (Satisfacción en tickets × 0.15)
```

| Componente | Peso | Fuente |
|---|---|---|
| NPS normalizado | 30% | `nps_surveys.score` → escala 0-100 |
| Engagement Score | 30% | `product_events` → frecuencia, variedad, profundidad, colaboración |
| Historial de pagos | 25% | `payments` → ratio de pagos exitosos |
| Satisfacción en tickets | 15% | `tickets.satisfaction` → escala 1-5 → 0-100 |
