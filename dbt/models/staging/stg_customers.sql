with source as (
    select * from bronze.customers
),
renamed as (
    select
        customer_id,
        company_id,
        full_name,
        lower(trim(email))              as email,
        upper(country)                  as country,
        segment,
        plan,
        cast(mrr as decimal(10,2))      as mrr,
        cast(signup_date as date)       as signup_date,
        status,
        try_cast(churn_date as date)    as churn_date,
        activation_completed,
        is_b2b,
        _ingested_at,
        _batch_id
    from source
    where customer_id is not null
)
select * from renamed
