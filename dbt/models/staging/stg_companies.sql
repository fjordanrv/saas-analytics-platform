with source as (
    select * from bronze.companies
),
renamed as (
    select
        company_id,
        name                            as company_name,
        industry,
        cast(employee_count as integer) as employee_count,
        upper(country)                  as country,
        account_manager,
        cast(created_at as date)        as created_at,
        _ingested_at,
        _batch_id
    from source
    where company_id is not null
)
select * from renamed
