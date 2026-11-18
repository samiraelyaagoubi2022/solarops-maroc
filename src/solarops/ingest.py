"""Ingestion des données météo depuis Open-Meteo."""
import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY = ["shortwave_radiation", "temperature_2m", "cloud_cover", "wind_speed_10m"]


def fetch(latitude, longitude, start, end):
    """Télécharge la météo horaire d'un lieu entre deux dates."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start,
        "end_date": end,
        "hourly": ",".join(HOURLY),
        "timezone": "GMT",
    }
    response = requests.get(ARCHIVE_URL, params=params, timeout=60)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    data = fetch(35.2517, -3.9372, "2024-06-01", "2024-06-02")  # Al Hoceima
    print(list(data.keys()))
    print(list(data["hourly"].keys()))
    print(len(data["hourly"]["time"]))