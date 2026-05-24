"""
Generación de datos mock para CloudMetrics Inc.
Genera datos ficticios realistas para todas las tablas del pipeline.

Uso:
    python -m src.ingestion.generate_mock_data
"""

import calendar
import random
import uuid
import json
from collections import defaultdict
from datetime import datetime, timedelta, date
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker
from rich.console import Console
from rich.table import Table

from src.utils.logger import get_logger

fake = Faker()
log = get_logger(__name__)
console = Console()

random.seed(42)
np.random.seed(42)
Faker.seed(42)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ── Constantes ────────────────────────────────────────────────────────────────

PLANS = {
    "Starter":    {"weight": 0.35, "mrr_range": (49, 99)},
    "Pro":        {"weight": 0.30, "mrr_range": (149, 299)},
    "Business":   {"weight": 0.25, "mrr_range": (499, 999)},
    "Enterprise": {"weight": 0.10, "mrr_range": (1999, 4999)},
}
SEGMENTS = {"SMB": 0.60, "Mid-Market": 0.30, "Enterprise": 0.10}
COUNTRIES = {
    "US": 0.40, "GB": 0.15, "DE": 0.10, "ES": 0.08,
    "FR": 0.07, "CA": 0.05, "AU": 0.04, "NL": 0.03,
    "BR": 0.03, "MX": 0.05,
}
INDUSTRIES = [
    "SaaS", "Fintech", "E-commerce", "Healthcare",
    "EdTech", "Marketing", "HR Tech", "Logistics",
]
EVENT_TYPES = {
    "login": 0.35, "feature_use": 0.30, "export": 0.10,
    "api_call": 0.10, "invite": 0.08, "settings": 0.05,
    "billing": 0.02,
}
FEATURES = [
    "dashboard", "reports", "api_integration",
    "team_invite", "export_csv", "webhooks",
    "custom_fields", "automations", "analytics",
    "billing_management",
]
DEVICES = {"web": 0.65, "mobile": 0.25, "api": 0.10}
CHURN_RATE = 0.03
N_COMPANIES = 500
N_CUSTOMERS = 1000
N_EVENTS = 50000
N_LEADS = 3000
N_NPS = 1500
N_TICKETS = 1000

# Listas y pesos pre-computados para numpy
_PLAN_KEYS     = list(PLANS.keys())
_PLAN_WEIGHTS  = [PLANS[p]["weight"] for p in _PLAN_KEYS]
_SEG_KEYS      = list(SEGMENTS.keys())
_SEG_WEIGHTS   = list(SEGMENTS.values())
_COUNTRY_KEYS  = list(COUNTRIES.keys())
_COUNTRY_WEIGHTS = list(COUNTRIES.values())
_EVENT_KEYS    = list(EVENT_TYPES.keys())
_EVENT_WEIGHTS = list(EVENT_TYPES.values())
_DEVICE_KEYS   = list(DEVICES.keys())
_DEVICE_WEIGHTS = list(DEVICES.values())


# ── Generadores ───────────────────────────────────────────────────────────────

def generate_companies() -> pd.DataFrame:
    """Genera N_COMPANIES empresas ficticias.

    Employee count distribuido 60/30/10 entre SMB, Mid-Market y Enterprise.

    Returns:
        DataFrame con columnas: company_id, name, industry, employee_count,
        country, account_manager, created_at.
    """
    log.info(f"Generando {N_COMPANIES} empresas...")

    seg_draw  = np.random.choice(_SEG_KEYS, size=N_COMPANIES, p=_SEG_WEIGHTS)
    countries = np.random.choice(_COUNTRY_KEYS, size=N_COMPANIES, p=_COUNTRY_WEIGHTS)

    records = []
    for i in range(N_COMPANIES):
        seg = seg_draw[i]
        if seg == "SMB":
            emp = random.randint(1, 50)
        elif seg == "Mid-Market":
            emp = random.randint(51, 500)
        else:
            emp = random.randint(501, 5000)

        records.append({
            "company_id":      f"comp_{str(uuid.uuid4())[:8]}",
            "name":            fake.company(),
            "industry":        random.choice(INDUSTRIES),
            "employee_count":  emp,
            "country":         countries[i],
            "account_manager": fake.name(),
            "created_at":      fake.date_between(
                                   start_date=date(2020, 1, 1),
                                   end_date=date(2023, 1, 1)),
        })

    df = pd.DataFrame(records)
    log.info(f"Companies generadas: {len(df)}")
    return df


def generate_customers(companies_df: pd.DataFrame) -> pd.DataFrame:
    """Genera N_CUSTOMERS clientes con plan, MRR, status y fechas coherentes.

    80% son B2B (company_id asignado), 20% B2C (company_id = None).
    churn_date solo se asigna si status == 'churned'.

    Args:
        companies_df: DataFrame de empresas para asignar FKs B2B.

    Returns:
        DataFrame con columnas: customer_id, company_id, full_name, email,
        phone, country, segment, plan, mrr, signup_date, status, churn_date,
        activation_completed, is_b2b.
    """
    log.info(f"Generando {N_CUSTOMERS} clientes...")

    company_ids = companies_df["company_id"].tolist()

    statuses  = np.random.choice(
        ["active", "churned", "trial"], N_CUSTOMERS, p=[0.85, 0.12, 0.03]
    )
    plans     = np.random.choice(_PLAN_KEYS, N_CUSTOMERS, p=_PLAN_WEIGHTS)
    segments  = np.random.choice(_SEG_KEYS, N_CUSTOMERS, p=_SEG_WEIGHTS)
    countries = np.random.choice(_COUNTRY_KEYS, N_CUSTOMERS, p=_COUNTRY_WEIGHTS)

    records = []
    for i in range(N_CUSTOMERS):
        plan   = plans[i]
        status = statuses[i]
        mrr_lo, mrr_hi = PLANS[plan]["mrr_range"]
        mrr    = float(np.random.randint(mrr_lo, mrr_hi + 1))

        signup_date = fake.date_between(
            start_date=date(2022, 1, 1),
            end_date=date(2024, 6, 1),
        )

        churn_date = None
        if status == "churned":
            churn_date = signup_date + timedelta(days=random.randint(90, 730))

        is_b2b     = random.random() < 0.80
        company_id = random.choice(company_ids) if is_b2b else None
        activation = status == "active" and random.random() < 0.78

        records.append({
            "customer_id":          f"cust_{str(uuid.uuid4())[:8]}",
            "company_id":           company_id,
            "full_name":            fake.name(),
            "email":                fake.email(),
            "phone":                fake.phone_number(),
            "country":              countries[i],
            "segment":              segments[i],
            "plan":                 plan,
            "mrr":                  mrr,
            "signup_date":          signup_date,
            "status":               status,
            "churn_date":           churn_date,
            "activation_completed": activation,
            "is_b2b":               is_b2b,
        })

    df = pd.DataFrame(records)
    log.info(f"Customers generados: {len(df)}")
    return df


def generate_subscriptions(customers_df: pd.DataFrame) -> pd.DataFrame:
    """Genera una suscripción por cliente con status, previous_plan y change_reason coherentes.

    Para clientes active: 80% active, 12% upgraded, 8% downgraded.
    Para upgraded, previous_plan es el plan de tier inferior al actual.
    Para downgraded, previous_plan es el plan de tier superior al actual.

    Args:
        customers_df: DataFrame de clientes generado por generate_customers().

    Returns:
        DataFrame con columnas: sub_id, customer_id, company_id, plan, mrr,
        start_date, end_date, status, previous_plan, change_reason.
    """
    log.info("Generando suscripciones...")

    plan_tier = {p: i for i, p in enumerate(_PLAN_KEYS)}

    records = []
    for _, c in customers_df.iterrows():
        plan = c["plan"]
        tier = plan_tier[plan]

        if c["status"] == "churned":
            sub_status    = "cancelled"
            end_date      = c["churn_date"]
            change_reason = "cancellation"
        elif c["status"] == "trial":
            sub_status    = "active"
            end_date      = None
            change_reason = "trial_end"
        else:  # active
            r = random.random()
            if r < 0.80:
                sub_status    = "active"
                change_reason = None
            elif r < 0.92:   # siguiente 12 % → upgraded
                sub_status    = "upgraded"
                change_reason = "upgrade"
            else:             # último 8 % → downgraded
                sub_status    = "downgraded"
                change_reason = "downgrade"
            end_date = None

        prev_plan = None
        if sub_status == "upgraded":
            lower = _PLAN_KEYS[:tier]           # planes de tier inferior
            prev_plan = random.choice(lower) if lower else None
        elif sub_status == "downgraded":
            higher = _PLAN_KEYS[tier + 1:]      # planes de tier superior
            prev_plan = random.choice(higher) if higher else None

        records.append({
            "sub_id":        f"sub_{str(uuid.uuid4())[:8]}",
            "customer_id":   c["customer_id"],
            "company_id":    c["company_id"],
            "plan":          plan,
            "mrr":           c["mrr"],
            "start_date":    c["signup_date"],
            "end_date":      end_date,
            "status":        sub_status,
            "previous_plan": prev_plan,
            "change_reason": change_reason,
        })

    df = pd.DataFrame(records)
    log.info(f"Subscriptions generadas: {len(df)}")
    return df


def _next_month(d: date) -> date:
    """Avanza exactamente un mes respetando el último día del mes destino."""
    month = d.month % 12 + 1
    year  = d.year + (1 if d.month == 12 else 0)
    return d.replace(year=year, month=month,
                     day=min(d.day, calendar.monthrange(year, month)[1]))


def generate_payments(subscriptions_df: pd.DataFrame) -> pd.DataFrame:
    """Genera un pago mensual por suscripción activa (máx 24 pagos por sub).

    Distribución: paid 96%, failed 2%, refunded 2%.
    Método de pago: credit_card 60%, bank_transfer 25%, paypal 15%.

    Args:
        subscriptions_df: DataFrame generado por generate_subscriptions().

    Returns:
        DataFrame con columnas: payment_id, sub_id, customer_id, amount,
        payment_date, status, payment_method, attempt_number.
    """
    log.info("Generando pagos...")

    today       = date(2026, 5, 23)
    pay_methods = ["credit_card", "bank_transfer", "paypal"]
    pay_weights = [0.60, 0.25, 0.15]

    records = []
    for _, sub in subscriptions_df.iterrows():
        start = sub["start_date"]
        if not isinstance(start, date):
            start = pd.Timestamp(start).date()

        end_raw = sub["end_date"]
        if end_raw is None or (not isinstance(end_raw, date) and pd.isna(end_raw)):
            end = today
        elif not isinstance(end_raw, date):
            end = pd.Timestamp(end_raw).date()
        else:
            end = end_raw

        payment_date = start
        count = 0
        while payment_date <= end and count < 24:
            r = random.random()
            if r < 0.96:
                pay_status = "paid"
                attempt    = 1
            elif r < 0.98:
                pay_status = "failed"
                attempt    = random.randint(1, 3)
            else:
                pay_status = "refunded"
                attempt    = 1

            records.append({
                "payment_id":     f"pay_{str(uuid.uuid4())[:8]}",
                "sub_id":         sub["sub_id"],
                "customer_id":    sub["customer_id"],
                "amount":         sub["mrr"],
                "payment_date":   payment_date,
                "status":         pay_status,
                "payment_method": random.choices(pay_methods, weights=pay_weights)[0],
                "attempt_number": attempt,
            })
            payment_date = _next_month(payment_date)
            count += 1

    df = pd.DataFrame(records)
    log.info(f"Payments generados: {len(df)}")
    return df


def generate_events(customers_df: pd.DataFrame) -> pd.DataFrame:
    """Genera N_EVENTS eventos de producto para clientes activos y en trial.

    Sesiones: grupos de 3-8 eventos consecutivos del mismo cliente.
    Timestamps: 70% en días laborables, 60% en horario 8-18h UTC.

    Args:
        customers_df: DataFrame generado por generate_customers().

    Returns:
        DataFrame con columnas: event_id, customer_id, session_id, event_type,
        feature_name, timestamp, device, country.
    """
    log.info(f"Generando {N_EVENTS} eventos...")

    active_df    = customers_df[customers_df["status"].isin(["active", "trial"])]
    active_ids   = active_df["customer_id"].tolist()
    cust_country = dict(zip(active_df["customer_id"], active_df["country"]))

    # Asignaciones vectorizadas
    customer_ids = np.random.choice(active_ids, size=N_EVENTS)
    event_types  = np.random.choice(_EVENT_KEYS, size=N_EVENTS, p=_EVENT_WEIGHTS)
    devices      = np.random.choice(_DEVICE_KEYS, size=N_EVENTS, p=_DEVICE_WEIGHTS)

    # Timestamps — vectorizado con pandas
    base        = pd.Timestamp("2026-05-23")
    day_offsets = np.random.randint(0, 90, N_EVENTS)
    event_dates = pd.Series(base - pd.to_timedelta(day_offsets, unit="D"))

    # 70 % días laborables: ajustar sábado→viernes, domingo→lunes
    dow          = event_dates.dt.dayofweek   # 0=lun … 6=dom
    weekday_mask = np.random.random(N_EVENTS) < 0.70
    adj_days     = np.zeros(N_EVENTS, dtype=int)
    adj_days[(dow.values == 5) & weekday_mask] = -1   # sábado → viernes
    adj_days[(dow.values == 6) & weekday_mask] =  1   # domingo → lunes
    event_dates = event_dates + pd.to_timedelta(adj_days, unit="D")

    # 60 % horario laboral (8-18h), 40 % cualquier hora
    n_biz   = int(N_EVENTS * 0.60)
    hours   = np.concatenate([np.random.randint(8, 18, n_biz),
                               np.random.randint(0, 24, N_EVENTS - n_biz)])
    np.random.shuffle(hours)
    minutes = np.random.randint(0, 60, N_EVENTS)
    seconds = np.random.randint(0, 60, N_EVENTS)

    timestamps = (event_dates.dt.normalize()
                  + pd.to_timedelta(hours,   unit="h")
                  + pd.to_timedelta(minutes, unit="m")
                  + pd.to_timedelta(seconds, unit="s"))

    # Sesiones: grupos de 3-8 eventos consecutivos por cliente
    cust_to_indices: dict[str, list[int]] = defaultdict(list)
    for idx, cid in enumerate(customer_ids):
        cust_to_indices[cid].append(idx)

    session_ids = [""] * N_EVENTS
    for indices in cust_to_indices.values():
        k = 0
        while k < len(indices):
            sid   = f"sess_{str(uuid.uuid4())[:8]}"
            batch = random.randint(3, 8)
            for idx in indices[k: k + batch]:
                session_ids[idx] = sid
            k += batch

    # feature_name solo para event_type == "feature_use"
    features = [random.choice(FEATURES) if et == "feature_use" else None
                for et in event_types]

    df = pd.DataFrame({
        "event_id":     [f"evt_{str(uuid.uuid4())[:8]}" for _ in range(N_EVENTS)],
        "customer_id":  customer_ids,
        "session_id":   session_ids,
        "event_type":   event_types,
        "feature_name": features,
        "timestamp":    timestamps,
        "device":       devices,
        "country":      [cust_country.get(cid, "US") for cid in customer_ids],
    })

    log.info(f"Events generados: {len(df)}, sesiones únicas: {df['session_id'].nunique()}")
    return df


def generate_leads() -> pd.DataFrame:
    """Genera N_LEADS leads de marketing con atribución last-touch y CAC por canal.

    Distribución de fuentes: organic 30%, paid_search 25%, referral 20%,
    email 15%, social 10%. Tasa de conversión: 33%.

    Returns:
        DataFrame con columnas: lead_id, email, source, campaign, channel,
        lead_date, converted, conversion_date, cac_usd.
    """
    log.info(f"Generando {N_LEADS} leads...")

    sources        = ["organic", "paid_search", "referral", "email", "social"]
    source_weights = [0.30, 0.25, 0.20, 0.15, 0.10]
    channel_map    = {
        "organic":     "Blog",
        "paid_search": "Google",
        "referral":    "Referral",
        "email":       "Newsletter",
    }
    social_channels = ["LinkedIn", "Facebook", "Twitter"]
    today           = date(2026, 5, 23)
    start_date      = today - timedelta(days=365)

    sources_arr  = np.random.choice(sources, size=N_LEADS, p=source_weights)
    converted    = np.random.random(N_LEADS) < 0.33

    records = []
    for i in range(N_LEADS):
        source    = sources_arr[i]
        lead_date = fake.date_between(start_date=start_date, end_date=today)
        is_conv   = bool(converted[i])

        conv_date = None
        if is_conv:
            conv_date = lead_date + timedelta(days=random.randint(1, 30))
            if conv_date > today:
                conv_date = today

        cac_map = {
            "organic":     0.0,
            "paid_search": float(random.randint(180, 350)),
            "referral":    float(random.randint(50, 120)),
            "email":       float(random.randint(30, 80)),
            "social":      float(random.randint(90, 200)),
        }
        channel = random.choice(social_channels) if source == "social" else channel_map[source]

        records.append({
            "lead_id":         f"lead_{str(uuid.uuid4())[:8]}",
            "email":           fake.email(),
            "source":          source,
            "campaign":        fake.catch_phrase(),
            "channel":         channel,
            "lead_date":       lead_date,
            "converted":       is_conv,
            "conversion_date": conv_date,
            "cac_usd":         cac_map[source],
        })

    df = pd.DataFrame(records)
    log.info(f"Leads generados: {len(df)}")
    return df


def generate_nps_surveys(customers_df: pd.DataFrame) -> pd.DataFrame:
    """Genera N_NPS encuestas NPS de clientes activos con health_score correlacionado.

    Distribución de scores: promoters 60% (9-10), passives 25% (7-8),
    detractors 15% (0-6). Comentario siempre para promoters/detractors,
    50% para passives.

    Args:
        customers_df: DataFrame generado por generate_customers().

    Returns:
        DataFrame con columnas: nps_id, customer_id, score, category,
        survey_date, comment, health_score.
    """
    log.info(f"Generando {N_NPS} encuestas NPS...")

    active   = customers_df[customers_df["status"] == "active"]
    sampled  = active.sample(n=N_NPS, replace=True, random_state=42).reset_index(drop=True)
    today    = date(2026, 5, 23)
    start    = today - timedelta(days=180)

    records = []
    for _, c in sampled.iterrows():
        r = random.random()
        if r < 0.60:
            score    = random.randint(9, 10)
            category = "promoter"
            hs       = random.randint(70, 100)
            comment  = fake.sentence()
        elif r < 0.85:
            score    = random.randint(7, 8)
            category = "passive"
            hs       = random.randint(40, 70)
            comment  = fake.sentence() if random.random() < 0.50 else None
        else:
            score    = random.randint(0, 6)
            category = "detractor"
            hs       = random.randint(0, 40)
            comment  = fake.sentence()

        records.append({
            "nps_id":       f"nps_{str(uuid.uuid4())[:8]}",
            "customer_id":  c["customer_id"],
            "score":        score,
            "category":     category,
            "survey_date":  fake.date_between(start_date=start, end_date=today),
            "comment":      comment,
            "health_score": float(hs),
        })

    df = pd.DataFrame(records)
    log.info(f"NPS surveys generadas: {len(df)}")
    return df


def generate_tickets(customers_df: pd.DataFrame) -> pd.DataFrame:
    """Genera N_TICKETS tickets de soporte con TTR y satisfacción correlacionados.

    TTR por prioridad: critical 1-4h, high 4-24h, medium 24-72h, low 72-168h.
    Satisfacción 4-5 si resuelto en la mitad inferior del rango, 2-3 si en la superior.

    Args:
        customers_df: DataFrame generado por generate_customers().

    Returns:
        DataFrame con columnas: ticket_id, customer_id, type, priority, status,
        created_at, resolved_at, satisfaction.
    """
    log.info(f"Generando {N_TICKETS} tickets...")

    t_types   = ["bug", "feature_request", "billing", "onboarding"]
    t_weights = [0.30, 0.25, 0.20, 0.25]
    prios     = ["low", "medium", "high", "critical"]
    p_weights = [0.40, 0.35, 0.20, 0.05]
    statuses  = ["open", "in_progress", "resolved", "closed"]
    s_weights = [0.20, 0.30, 0.40, 0.10]

    # (min_hours, max_hours) por prioridad
    ttr_range = {"critical": (1, 4), "high": (4, 24), "medium": (24, 72), "low": (72, 168)}

    sampled    = customers_df.sample(n=N_TICKETS, replace=True, random_state=42).reset_index(drop=True)
    types_arr  = np.random.choice(t_types, N_TICKETS, p=t_weights)
    prio_arr   = np.random.choice(prios,   N_TICKETS, p=p_weights)
    status_arr = np.random.choice(statuses, N_TICKETS, p=s_weights)
    today_dt   = datetime(2026, 5, 23, 23, 59, 59)
    start_date = date(2026, 5, 23) - timedelta(days=180)

    records = []
    for i, (_, c) in enumerate(sampled.iterrows()):
        priority = prio_arr[i]
        status   = status_arr[i]

        created_at = datetime.combine(
            fake.date_between(start_date=start_date, end_date=date(2026, 5, 23)),
            fake.time_object(),
        )

        resolved_at  = None
        satisfaction = None

        if status in ("resolved", "closed"):
            lo, hi        = ttr_range[priority]
            elapsed_hours = random.uniform(lo, hi)
            resolved_at   = created_at + timedelta(hours=elapsed_hours)
            if resolved_at > today_dt:
                resolved_at = today_dt

            # Fast = primera mitad del rango → 4-5; slow = segunda mitad → 2-3
            midpoint     = (lo + hi) / 2
            satisfaction = random.randint(4, 5) if elapsed_hours <= midpoint else random.randint(2, 3)

        records.append({
            "ticket_id":   f"tick_{str(uuid.uuid4())[:8]}",
            "customer_id": c["customer_id"],
            "type":        types_arr[i],
            "priority":    priority,
            "status":      status,
            "created_at":  created_at,
            "resolved_at": resolved_at,
            "satisfaction": satisfaction,
        })

    df = pd.DataFrame(records)
    log.info(f"Tickets generados: {len(df)}")
    return df


# ── Pipeline principal ────────────────────────────────────────────────────────

def main() -> None:
    """Genera todos los datasets mock y los guarda en data/raw/."""
    log.info("=== Iniciando generación de datos mock — CloudMetrics Inc. ===")

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    companies     = generate_companies()
    customers     = generate_customers(companies)
    subscriptions = generate_subscriptions(customers)
    payments      = generate_payments(subscriptions)
    events        = generate_events(customers)
    leads         = generate_leads()
    nps           = generate_nps_surveys(customers)
    tickets       = generate_tickets(customers)

    # (nombre_tabla, dataframe, nombre_archivo_csv)
    datasets = [
        ("crm_companies",         companies,     "crm_companies.csv"),
        ("crm_customers",         customers,     "crm_customers.csv"),
        ("billing_subscriptions", subscriptions, "billing_subscriptions.csv"),
        ("billing_payments",      payments,      "billing_payments.csv"),
        ("product_events",        events,        "product_events.csv"),
        ("marketing_leads",       leads,         "marketing_leads.csv"),
        ("nps_surveys",           nps,           "nps_surveys.csv"),
        ("support_tickets",       tickets,       "support_tickets.csv"),
    ]

    for _, df, filename in datasets:
        path = RAW_DIR / filename
        df.to_csv(path, index=False)
        log.info(f"Guardado: {filename} ({len(df):,} filas)")

    # product_events también como JSON
    json_path = RAW_DIR / "product_events.json"
    events.to_json(json_path, orient="records", date_format="iso", indent=2)
    log.info(f"Guardado: product_events.json ({len(events):,} filas)")

    # Tabla resumen con rich
    table = Table(title="CloudMetrics Mock Data — Resumen", show_lines=True)
    table.add_column("Tabla",   style="cyan",  no_wrap=True)
    table.add_column("Filas",   style="green", justify="right")
    table.add_column("Archivo", style="dim")

    for name, df, filename in datasets:
        fmt = ".csv + .json" if name == "product_events" else ".csv"
        table.add_row(name, f"{len(df):,}", fmt)

    console.print(table)
    log.info("=== Generación completada ===")


if __name__ == "__main__":
    main()
