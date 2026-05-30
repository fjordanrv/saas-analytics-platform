-- Grain: 1 fila por customer_id por mes
-- KPI: MRR con movimientos calculados dinámicamente mes a mes
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
monthly_spine as (
    select
        sm.customer_id,
        sm.plan,
        sm.mrr,
        sm.start_date,
        sm.end_date,
        {% if target.type == 'databricks' %}
        explode(sequence(
            date_trunc('month', sm.start_date),
            date_trunc('month', coalesce(sm.end_date, TO_DATE('2024-05-31'))),
            interval 1 month
        )) as month
        {% else %}
        unnest(range(
            date_trunc('month', sm.start_date::date),
            date_trunc('month', coalesce(sm.end_date, date('2024-05-31'))::date) + interval '1 month',
            interval '1 month'
        )) as month
        {% endif %}
    from subscription_metrics sm
),
monthly_mrr as (
    select
        ms.customer_id,
        cl.segment,
        cl.country,
        ms.plan,
        ms.month,
        ms.mrr
    from monthly_spine ms
    left join customer_lifecycle cl using (customer_id)
),
mrr_with_lag as (
    select
        *,
        lag(mrr) over (
            partition by customer_id
            order by month
        ) as prev_mrr
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
        case
            when prev_mrr is null then 'new'
            when mrr > prev_mrr   then 'expansion'
            when mrr < prev_mrr   then 'contraction'
            when mrr = 0          then 'churned'
            else                       'retained'
        end                                            as mrr_movement_type,
        case
            when prev_mrr is null then mrr
            when mrr > prev_mrr   then mrr - prev_mrr
            when mrr < prev_mrr   then mrr - prev_mrr
            else 0
        end                                            as mrr_movement_amount,
        case
            when prev_mrr is null then mrr
            else 0
        end                                            as new_mrr,
        case
            when prev_mrr is not null and mrr > prev_mrr then mrr - prev_mrr
            else 0
        end                                            as expansion_mrr,
        case
            when prev_mrr is not null and mrr < prev_mrr then prev_mrr - mrr
            else 0
        end                                            as contraction_mrr,
        case
            when mrr = 0 then prev_mrr
            else 0
        end                                            as churned_mrr,
        current_timestamp                              as updated_at
    from mrr_with_lag
)
select * from mrr_final