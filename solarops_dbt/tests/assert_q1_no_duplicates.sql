-- Échoue si une combinaison (ville, heure) apparaît plus d'une fois
select city, time_utc, count(*) as nb
from {{ ref('stg_weather_hourly') }}
group by city, time_utc
having count(*) > 1