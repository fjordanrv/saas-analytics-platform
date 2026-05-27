with source as (
    select * from bronze.nps_surveys
),
renamed as (
    select
        nps_id,
        customer_id,
        cast(score as integer)          as nps_score,
        category                        as nps_category,
        cast(survey_date as date)       as survey_date,
        comment,
        cast(health_score as decimal(5,2)) as health_score,
        _ingested_at,
        _batch_id
    from source
    where nps_id is not null
)
select * from renamed
