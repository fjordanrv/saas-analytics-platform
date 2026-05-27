-- Grain: 1 fila por customer_id
-- KPI: Activation Rate — 3 pasos en 14 días

with customers as (
    select
        customer_id,
        signup_date,
        segment,
        plan,
        status
    from {{ ref('int_customer_lifecycle') }}
),
engagement as (
    select
        customer_id,
        login_count_30d,
        unique_features_30d,
        invite_count_30d,
        last_login_at
    from {{ ref('int_product_engagement') }}
),
activation as (
    select
        c.customer_id,
        c.signup_date,
        c.segment,
        c.plan,
        c.status,
        date_trunc('month', c.signup_date)             as signup_month,
        -- Paso 1: tuvo al menos 1 login
        case when e.login_count_30d > 0
             then true else false end                  as step1_login,
        -- Paso 2: usó al menos 1 feature
        case when e.unique_features_30d > 0
             then true else false end                  as step2_feature,
        -- Paso 3: invitó a alguien
        case when e.invite_count_30d > 0
             then true else false end                  as step3_invite,
        -- Activado = completó los 3 pasos
        case when e.login_count_30d > 0
              and e.unique_features_30d > 0
              and e.invite_count_30d > 0
             then true else false end                  as is_activated,
        current_timestamp                              as updated_at
    from customers c
    left join engagement e using (customer_id)
)
select * from activation
