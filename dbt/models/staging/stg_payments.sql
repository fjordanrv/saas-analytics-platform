with source as (
    select * from bronze.payments
),
renamed as (
    select
        payment_id,
        sub_id,
        customer_id,
        cast(amount as decimal(10,2))   as amount,
        cast(payment_date as date)      as payment_date,
        status                          as payment_status,
        payment_method,
        cast(attempt_number as integer) as attempt_number,
        _ingested_at,
        _batch_id
    from source
    where payment_id is not null
)
select * from renamed
