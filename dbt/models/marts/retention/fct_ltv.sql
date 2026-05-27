-- Grain: 1 fila por segmento y plan
-- KPI: LTV, LTV/CAC, Payback Period

with mrr_by_segment as (
    select
        segment,
        plan,
        avg(mrr)                                       as avg_mrr,
        count(distinct customer_id)                    as total_customers
    from {{ ref('fct_mrr') }}
    where mrr_movement_type != 'churned'
    group by segment, plan
),
churn_by_segment as (
    select
        segment,
        avg(logo_churn_rate_pct) / 100.0               as avg_monthly_churn_rate
    from {{ ref('fct_churn') }}
    group by segment
),
cac_by_segment as (
    select
        avg(cac_usd)                                   as avg_cac
    from {{ ref('fct_customer_acquisition') }}
    where cac_usd > 0
),
ltv_metrics as (
    select
        m.segment,
        m.plan,
        m.total_customers,
        round(m.avg_mrr, 2)                            as avg_mrr,
        round(c.avg_monthly_churn_rate * 100, 2)       as monthly_churn_rate_pct,
        round(
            m.avg_mrr /
            nullif(c.avg_monthly_churn_rate, 0)
        , 2)                                           as ltv,
        round(
            m.avg_mrr /
            nullif(c.avg_monthly_churn_rate, 0) * 12
        , 2)                                           as ltv_annual,
        round(
            (m.avg_mrr / nullif(c.avg_monthly_churn_rate, 0)) /
            nullif(ca.avg_cac, 0)
        , 2)                                           as ltv_cac_ratio,
        round(
            ca.avg_cac /
            nullif(m.avg_mrr, 0)
        , 2)                                           as payback_period_months,
        current_timestamp                              as updated_at
    from mrr_by_segment m
    left join churn_by_segment c using (segment)
    cross join cac_by_segment ca
)
select * from ltv_metrics
order by ltv desc
