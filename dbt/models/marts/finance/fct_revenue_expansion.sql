-- Grain: 1 fila por mes
-- KPI: NRR, ARR, Net New MRR

with mrr as (
    select * from {{ ref('fct_mrr') }}
),
monthly_summary as (
    select
        month,
        sum(mrr)                                       as total_mrr,
        sum(mrr) * 12                                  as arr,
        sum(new_mrr)                                   as new_mrr,
        sum(expansion_mrr)                             as expansion_mrr,
        sum(contraction_mrr)                           as contraction_mrr,
        sum(churned_mrr)                               as churned_mrr,
        sum(new_mrr) + sum(expansion_mrr) +
        sum(contraction_mrr) - sum(churned_mrr)        as net_new_mrr,
        count(distinct customer_id)                    as active_customers
    from mrr
    group by month
),
nrr_calculated as (
    select
        month,
        total_mrr,
        arr,
        new_mrr,
        expansion_mrr,
        contraction_mrr,
        churned_mrr,
        net_new_mrr,
        active_customers,
        lag(total_mrr) over (order by month)           as prev_month_mrr,
        round(
            (total_mrr - new_mrr) /
            nullif(lag(total_mrr) over (order by month), 0) * 100
        , 2)                                           as nrr,
        current_timestamp                              as updated_at
    from monthly_summary
)
select * from nrr_calculated
