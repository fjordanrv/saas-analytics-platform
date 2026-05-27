with source as (
    select * from bronze.product_events
),
renamed as (
    select
        event_id,
        customer_id,
        session_id,
        event_type,
        feature_name,
        cast(timestamp as timestamp)    as event_timestamp,
        device,
        upper(country)                  as country,
        _ingested_at,
        _batch_id
    from source
    where event_id is not null
)
select * from renamed
