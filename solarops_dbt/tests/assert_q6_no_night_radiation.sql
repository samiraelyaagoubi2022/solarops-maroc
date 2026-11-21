-- Échoue si on trouve du rayonnement la nuit (0h à 3h UTC)
select *
from {{ ref('stg_weather_hourly') }}
where extract(hour from time_utc) between 0 and 3
  and shortwave_radiation > 1