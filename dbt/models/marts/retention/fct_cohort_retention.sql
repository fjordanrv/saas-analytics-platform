-- Grain: 1 fila por cohort_month y months_since_signup
-- KPI: Cohort Retention Rate

with customers as (
    select
        customer_id,
        segment,
        signup_date,
        status,
        churn_date,
        date_trunc('month', signup_date)               as cohort_month
    from {{ ref('int_customer_lifecycle') }}
),
cohort_size as (
    select
        cohort_month,
        count(customer_id)                             as cohort_size
    from customers
    group by cohort_month
),
retention_data as (
    select
        c.cohort_month,
        cs.cohort_size,
        months_series.months_since_signup,
        count(
            case
                when c.status = 'active'
                  or (c.churn_date is not null
                      and datediff('month', c.signup_date, c.churn_date)
                          > months_series.months_since_signup)
                then c.customer_id
            end
        )                                              as retained_customers
    from customers c
    join cohort_size cs using (cohort_month)
    cross join (
        select unnest(range(0, 13)) as months_since_signup
    ) months_series
    group by c.cohort_month, cs.cohort_size,
             months_series.months_since_signup
),
cohort_retention as (
    select
        cohort_month,
        cohort_size,
        months_since_signup,
        retained_customers,
        round(
            retained_customers * 100.0 /
            nullif(cohort_size, 0)
        , 2)                                           as retention_rate_pct,
        current_timestamp                              as updated_at
    from retention_data
)
select * from cohort_retention
order by cohort_month, months_since_signup
