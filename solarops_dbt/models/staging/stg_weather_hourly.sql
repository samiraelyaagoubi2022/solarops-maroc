with raw as (
    select * from {{ source('raw_data', 'weather') }}
)

select
    -- On crée un identifiant unique (Q1)
    city || '_' || cast(time as varchar) as weather_id,
    
    -- Typage strict
    cast(time as timestamp) as time_utc,
    cast(city as varchar) as city,
    
    -- Variables
    cast(shortwave_radiation as double) as shortwave_radiation,
    cast(temperature_2m as double) as temperature_2m,
    cast(relative_humidity_2m as double) as relative_humidity_2m,
    cast(surface_pressure as double) as surface_pressure,
    cast(cloud_cover as double) as cloud_cover,
    cast(cloud_cover_low as double) as cloud_cover_low,
    cast(cloud_cover_mid as double) as cloud_cover_mid,
    cast(cloud_cover_high as double) as cloud_cover_high,
    cast(wind_speed_10m as double) as wind_speed_10m,
    cast(wind_direction_10m as double) as wind_direction_10m,
    cast(precipitation as double) as precipitation

from raw