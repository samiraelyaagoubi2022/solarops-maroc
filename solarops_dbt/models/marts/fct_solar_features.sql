{{ config(materialized='table') }}

with weather as (
    select * from {{ ref('stg_weather_hourly') }}
),

features as (
    select
        weather_id,
        city,
        time_utc,
        
        -- Variables météo de base
        shortwave_radiation,
        temperature_2m,
        relative_humidity_2m,
        surface_pressure,
        cloud_cover,
        cloud_cover_low,
        cloud_cover_mid,
        cloud_cover_high,
        wind_speed_10m,
        wind_direction_10m,
        precipitation,

        -- 1. ENCODAGE CYCLIQUE (Heure) : sin/cos
        sin(2 * pi() * extract(hour from time_utc) / 24) as hour_sin,
        cos(2 * pi() * extract(hour from time_utc) / 24) as hour_cos,

        -- 2. ENCODAGE CYCLIQUE (Mois) : sin/cos
        sin(2 * pi() * extract(month from time_utc) / 12) as month_sin,
        cos(2 * pi() * extract(month from time_utc) / 12) as month_cos,

        -- 3. FEATURES DE DÉCALAGE (Lags) : Valeur de J-1
        lag(shortwave_radiation, 24) over (partition by city order by time_utc) as radiation_lag_24h,

        -- 4. LA CIBLE (Target) : Puissance PV (hypothèse centrale 1000 kWc, PR 0.85)
        (shortwave_radiation / 1000.0) * 1000.0 * 0.85 as target_power_kw

    from weather
)

select * from features