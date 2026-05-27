with customers as (
    select * from {{ ref('stg_customers') }}
),
companies as (
    select * from {{ ref('stg_companies') }}
),
subscriptions as (
    select * from {{ ref('stg_subscriptions') }}
    where status = 'active'
),
customer_enriched as (
    select
        c.customer_id,
        c.company_id,
        c.full_name,
        c.email,
        c.country,
        c.segment,
        c.plan,
        c.mrr,
        c.signup_date,
        c.status,
        c.churn_date,
        c.activation_completed,
        c.is_b2b,
        co.company_name,
        co.industry,
        co.employee_count,
        co.account_manager,
        datediff('day', c.signup_date, current_date)   as customer_age_days,
        datediff('month', c.signup_date, current_date) as customer_age_months,
        case c.plan
            when 'Starter'    then 1
            when 'Pro'        then 2
            when 'Business'   then 3
            when 'Enterprise' then 4
        end                                            as plan_tier,
        case when c.plan = 'Enterprise'
             then true else false end                  as is_enterprise,
        case when c.status = 'active'
             then true else false end                  as is_active,
        case
            when c.churn_date is not null
            then datediff('day', c.signup_date, c.churn_date)
            else null
        end                                            as days_to_churn,
        s.sub_id,
        s.start_date                                   as sub_start_date,
        current_timestamp                              as updated_at
    from customers c
    left join companies co using (company_id)
    left join subscriptions s using (customer_id)
)
select * from customer_enriched
