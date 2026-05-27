with source as (
    select * from bronze.support_tickets
),
renamed as (
    select
        ticket_id,
        customer_id,
        type                            as ticket_type,
        priority,
        status                          as ticket_status,
        cast(created_at as timestamp)   as created_at,
        try_cast(resolved_at as timestamp) as resolved_at,
        satisfaction,
        _ingested_at,
        _batch_id
    from source
    where ticket_id is not null
)
select * from renamed
