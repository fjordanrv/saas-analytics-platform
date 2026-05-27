with source as (
    select * from bronze.subscriptions
),
renamed as (
    select
        sub_id,
        customer_id,
        company_id,
        plan,
        cast(mrr as decimal(10,2))      as mrr,
        cast(start_date as date)        as start_date,
        try_cast(end_date as date)      as end_date,
        status,
        previous_plan,
        change_reason,
        _ingested_at,
        _batch_id
    from source
    where sub_id is not null
)
select * from renamed
