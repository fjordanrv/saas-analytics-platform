with source as (
    select * from bronze.marketing_leads
),
renamed as (
    select
        lead_id,
        lower(trim(email))              as email,
        source                          as lead_source,
        campaign,
        channel,
        cast(lead_date as date)         as lead_date,
        cast(converted as boolean)      as converted,
        try_cast(conversion_date as date) as conversion_date,
        cast(cac_usd as decimal(10,2))  as cac_usd,
        _ingested_at,
        _batch_id
    from source
    where lead_id is not null
)
select * from renamed
