with subscriptions as (
    select * from {{ ref('stg_subscriptions') }}
),
payments as (
    select * from {{ ref('stg_payments') }}
),
payment_metrics as (
    select
        customer_id,
        count(payment_id)                              as total_payments,
        sum(case when payment_status = 'paid'
            then amount else 0 end)                    as total_paid_usd,
        sum(case when payment_status = 'failed'
            then 1 else 0 end)                         as failed_payments,
        sum(case when payment_status = 'refunded'
            then amount else 0 end)                    as total_refunded_usd,
        max(payment_date)                              as last_payment_date,
        avg(amount)                                    as avg_payment_amount
    from payments
    group by customer_id
),
subscription_metrics as (
    select
        s.customer_id,
        s.sub_id,
        s.plan,
        s.mrr,
        s.status,
        s.start_date,
        s.end_date,
        s.previous_plan,
        s.change_reason,
        datediff('month', s.start_date,
            coalesce(s.end_date, current_date))        as subscription_months,
        case
            when s.previous_plan is null then 'new'
            when s.change_reason = 'upgrade' then 'expansion'
            when s.change_reason = 'downgrade' then 'contraction'
            when s.status = 'cancelled' then 'churned'
            else 'retained'
        end                                            as mrr_movement_type,
        pm.total_payments,
        pm.total_paid_usd,
        pm.failed_payments,
        pm.total_refunded_usd,
        pm.last_payment_date,
        pm.avg_payment_amount,
        case when pm.failed_payments > 0
             then true else false end                  as has_payment_issues,
        current_timestamp                              as updated_at
    from subscriptions s
    left join payment_metrics pm using (customer_id)
)
select * from subscription_metrics
