-- On configure la sévérité à WARN (le pipeline ne s'arrête pas)
{{ config(severity='warn') }}

-- Échoue si la couverture totale est inférieure à une couche spécifique (-1 pt de tolérance)
select *
from {{ ref('stg_weather_hourly') }}
where cloud_cover < (cloud_cover_low - 1) 
   or cloud_cover < (cloud_cover_mid - 1) 
   or cloud_cover < (cloud_cover_high - 1)