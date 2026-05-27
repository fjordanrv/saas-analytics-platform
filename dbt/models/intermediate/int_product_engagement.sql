with events as (
    select * from {{ ref('stg_product_events') }}
    where event_timestamp >= current_date - interval '30 days'
),
customers as (
    select customer_id, plan, segment
    from {{ ref('stg_customers') }}
    where status in ('active', 'trial')
),
event_metrics as (
    select
        customer_id,
        count(event_id)                                as total_events,
        count(distinct session_id)                     as total_sessions,
        count(distinct
            case when event_type = 'feature_use'
            then feature_name end)                     as unique_features_used,
        count(distinct
            date_trunc('day', event_timestamp))        as active_days,
        max(event_timestamp)                           as last_event_at,
        max(case when event_type = 'login'
            then event_timestamp end)                  as last_login_at,
        count(case when event_type = 'login'
            then 1 end)                                as login_count,
        count(case when event_type = 'invite'
            then 1 end)                                as invite_count,
        count(case when event_type = 'api_call'
            then 1 end)                                as api_call_count
    from events
    group by customer_id
),
engagement_scored as (
    select
        c.customer_id,
        c.plan,
        c.segment,
        coalesce(em.total_events, 0)                   as total_events_30d,
        coalesce(em.total_sessions, 0)                 as total_sessions_30d,
        coalesce(em.unique_features_used, 0)           as unique_features_30d,
        coalesce(em.active_days, 0)                    as active_days_30d,
        coalesce(em.login_count, 0)                    as login_count_30d,
        coalesce(em.invite_count, 0)                   as invite_count_30d,
        coalesce(em.api_call_count, 0)                 as api_call_count_30d,
        em.last_login_at,
        em.last_event_at,
        round(
            least(coalesce(em.login_count, 0) / 30.0, 1) * 30 +
            least(coalesce(em.unique_features_used, 0) / 10.0, 1) * 30 +
            least(coalesce(em.total_events, 0) / 50.0, 1) * 25 +
            case when coalesce(em.invite_count, 0) > 0
                 then 15 else 0 end
        , 2)                                           as engagement_score,
        current_timestamp                              as updated_at
    from customers c
    left join event_metrics em using (customer_id)
)
select * from engagement_scored
