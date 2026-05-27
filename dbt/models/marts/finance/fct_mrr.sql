-- Grain: 1 fila por customer_id por mes
-- KPI: MRR con movimientos New/Expansion/Contraction/Churned

with subscription_metrics as (
    select * from {{ ref('int_subscription_metrics') }}
),
customer_lifecycle as (
    select
        customer_id,
        segment,
        country,
        signup_date,
        status,
        churn_date
    from {{ ref('int_customer_lifecycle') }}
),
monthly_mrr as (
    select
        sm.customer_id,
        cl.segment,
        cl.country,
        sm.plan,
        date_trunc('month', sm.start_date)             as month,
        sm.mrr,
        sm.mrr_movement_type,
        sm.subscription_months
    from subscription_metrics sm
    left join customer_lifecycle cl using (customer_id)
),
mrr_with_lag as (
    select
        *,
        lag(mrr) over (
            partition by customer_id
            order by month
        )                                              as prev_mrr
    from monthly_mrr
),
mrr_final as (
    select
        customer_id,
        segment,
        country,
        plan,
        month,
        mrr,
        prev_mrr,
        mrr_movement_type,
        case
            when prev_mrr is null     then mrr
            when mrr > prev_mrr       then mrr - prev_mrr
            when mrr < prev_mrr       then mrr - prev_mrr
            else 0
        end                                            as mrr_movement_amount,
        case
            when mrr_movement_type = 'new'
            then mrr else 0
        end                                            as new_mrr,
        case
            when mrr_movement_type = 'expansion'
            then mrr - prev_mrr else 0
        end                                            as expansion_mrr,
        case
            when mrr_movement_type = 'contraction'
            then mrr - prev_mrr else 0
        end                                            as contraction_mrr,
        case
            when mrr_movement_type = 'churned'
            then mrr else 0
        end                                            as churned_mrr,
        current_timestamp                              as updated_at
    from mrr_with_lag
)
select * from mrr_final
