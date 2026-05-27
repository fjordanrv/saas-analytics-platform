-- Grain: 1 fila por mes y segmento
-- KPI: Logo Churn Rate y Revenue Churn Rate

with customers as (
    select
        customer_id,
        segment,
        plan,
        mrr,
        signup_date,
        status,
        churn_date,
        date_trunc('month', signup_date)               as signup_month,
        date_trunc('month', churn_date)                as churn_month
    from {{ ref('int_customer_lifecycle') }}
),
active_per_month as (
    select
        date_trunc('month', signup_date)               as month,
        segment,
        count(customer_id)                             as customers_start,
        sum(mrr)                                       as mrr_start
    from customers
    group by date_trunc('month', signup_date), segment
),
churned_per_month as (
    select
        churn_month                                    as month,
        segment,
        count(customer_id)                             as churned_customers,
        sum(mrr)                                       as churned_mrr
    from customers
    where status = 'churned'
      and churn_date is not null
    group by churn_month, segment
),
churn_metrics as (
    select
        a.month,
        a.segment,
        a.customers_start,
        a.mrr_start,
        coalesce(c.churned_customers, 0)               as churned_customers,
        coalesce(c.churned_mrr, 0)                     as churned_mrr,
        round(
            coalesce(c.churned_customers, 0) * 100.0 /
            nullif(a.customers_start, 0)
        , 2)                                           as logo_churn_rate_pct,
        round(
            coalesce(c.churned_mrr, 0) * 100.0 /
            nullif(a.mrr_start, 0)
        , 2)                                           as revenue_churn_rate_pct,
        current_timestamp                              as updated_at
    from active_per_month a
    left join churned_per_month c
        on a.month = c.month
        and a.segment = c.segment
)
select * from churn_metrics
