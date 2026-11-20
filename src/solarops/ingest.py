"""Ingestion des données météo Open-Meteo vers des fichiers Parquet.

Un fichier par ville et par année : data/raw/<ville>/<année>.parquet
"""
import argparse
import csv
import logging
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY = [
    "shortwave_radiation",  # la cible à prévoir
    "temperature_2m",
    "relative_humidity_2m",
    "surface_pressure",
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "wind_speed_10m",
    "wind_direction_10m",
    "precipitation",
]
COLUMNS = ["time", *HOURLY]
EXPECTED_KEYS = set(COLUMNS)
RETRIES = 4
# Fenêtre fixe par défaut : mêmes données à chaque exécution (reproductibilité)
DEFAULT_START_YEAR = 2015
DEFAULT_END_DATE = "2024-12-31"


def load_cities(path="config/cities.csv"):
    """Lit la liste des villes (nom, latitude, longitude) dans un fichier CSV."""
    with open(path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def year_ranges(start_year, end_date):
    """Découpe la période en années : [(année, début, fin), ...].

    La dernière année est tronquée à `end_date` si elle n'est pas complète.
    """
    last = date.fromisoformat(end_date)
    ranges = []
    for year in range(start_year, last.year + 1):
        end = min(date(year, 12, 31), last)
        ranges.append((year, date(year, 1, 1).isoformat(), end.isoformat()))
    return ranges


def fetch(latitude, longitude, start, end, retries=RETRIES):
    """Télécharge la météo horaire d'un lieu, avec nouvel essai en cas de panne."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start,
        "end_date": end,
        "hourly": ",".join(HOURLY),
        "timezone": "GMT",
    }
    for attempt in range(retries):
        try:
            response = requests.get(ARCHIVE_URL, params=params, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as error:
            status = getattr(error.response, "status_code", None)
            # On ne réessaie que pour une panne réseau, un quota (429) ou une
            # erreur du serveur (5xx). Une erreur 400 sera la même au 2e essai.
            retryable = status is None or status == 429 or status >= 500
            if not retryable or attempt == retries - 1:
                raise
            wait = 2**attempt
            logger.warning("Échec (%s), nouvel essai dans %s s", error, wait)
            time.sleep(wait)


def to_frame(payload, city):
    """Transforme la réponse JSON en tableau, après vérification du schéma."""
    hourly = payload.get("hourly")
    if hourly is None or not EXPECTED_KEYS <= hourly.keys():
        found = sorted(hourly.keys()) if hourly else None
        raise ValueError(
            f"Schéma inattendu pour {city}: "
            f"attendu {sorted(EXPECTED_KEYS)}, reçu {found}"
        )
    df = pd.DataFrame({column: hourly[column] for column in COLUMNS})
    df.insert(0, "city", city)
    return df


def parquet_path(out_dir, city, year):
    """Chemin du fichier d'une ville et d'une année (nom stable)."""
    return Path(out_dir) / city.replace(" ", "_") / f"{year}.parquet"


def write_parquet(df, out_dir, city, year):
    """Écrit le fichier d'une ville et d'une année (idempotent)."""
    target = parquet_path(out_dir, city, year)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    df.to_parquet(tmp, index=False)
    tmp.replace(target)  # remplacement en une opération : jamais à moitié écrit
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ingestion Open-Meteo vers Parquet")
    parser.add_argument("--start-year", type=int, default=DEFAULT_START_YEAR)
    parser.add_argument(
        "--end-date", default=DEFAULT_END_DATE, help="Dernier jour (AAAA-MM-JJ)"
    )
    parser.add_argument(
        "--cities", nargs="*", help="Villes à traiter (par défaut : toutes)"
    )
    parser.add_argument("--cities-file", default="config/cities.csv")
    parser.add_argument("--out", default="data/raw")
    parser.add_argument(
        "--force", action="store_true", help="Retélécharge aussi les années présentes"
    )
    parser.add_argument(
        "--pause", type=float, default=1.0, help="Pause (s) entre deux requêtes"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    periods = year_ranges(args.start_year, args.end_date)
    for city in load_cities(args.cities_file):
        name = city["city"]
        if args.cities and name not in args.cities:
            continue
        for year, start, end in periods:
            path = parquet_path(args.out, name, year)
            year_is_complete = end == f"{year}-12-31"
            if year_is_complete and path.exists() and not args.force:
                logger.info("%s %d : déjà présent, ignoré", name, year)
                continue
            payload = fetch(city["latitude"], city["longitude"], start, end)
            df = to_frame(payload, name)
            write_parquet(df, args.out, name, year)
            logger.info("%s %d : %d lignes -> %s", name, year, len(df), path)
            if args.pause:
                time.sleep(args.pause)


if __name__ == "__main__":
    main()
