-- Grain: 1 fila por mes y canal
-- KPI: New Customers, CAC por canal

with customers as (
    select
        customer_id,
        segment,
        plan,
        mrr,
        date_trunc('month', signup_date)               as signup_month
    from {{ ref('int_customer_lifecycle') }}
),
leads as (
    select
        lead_source,
        channel,
        date_trunc('month', lead_date)                 as lead_month,
        count(lead_id)                                 as total_leads,
        count(case when converted then 1 end)          as converted_leads,
        sum(cac_usd)                                   as total_cac_spend
    from {{ ref('stg_marketing_leads') }}
    group by lead_source, channel, lead_month
),
new_customers as (
    select
        signup_month                                   as month,
        segment,
        plan,
        count(customer_id)                             as new_customers,
        sum(mrr)                                       as new_mrr
    from customers
    group by signup_month, segment, plan
),
acquisition_metrics as (
    select
        l.lead_month                                   as month,
        l.lead_source,
        l.channel,
        l.total_leads,
        l.converted_leads,
        l.total_cac_spend,
        round(
            l.converted_leads * 100.0 /
            nullif(l.total_leads, 0)
        , 2)                                           as conversion_rate_pct,
        round(
            l.total_cac_spend /
            nullif(l.converted_leads, 0)
        , 2)                                           as cac_usd,
        current_timestamp                              as updated_at
    from leads l
)
select * from acquisition_metrics
