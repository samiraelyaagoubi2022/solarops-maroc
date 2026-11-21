-- Échoue si un jour n'a pas exactement 24 lignes pour une ville
select 
    city, 
    cast(time_utc as date) as jour, 
    count(*) as nb_heures
from {{ ref('stg_weather_hourly') }}
group by city, cast(time_utc as date)
having count(*) != 24