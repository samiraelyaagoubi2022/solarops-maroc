import pandas as pd
import pytest
import requests

from solarops import ingest

CITIES_CSV = (
    "city,latitude,longitude\n"
    "Tanger,35.7595,-5.8340\n"
    "Al Hoceima,35.2517,-3.9372\n"
)


def fake_payload():
    """Fausse réponse construite à partir de la liste réelle des variables."""
    hourly = {"time": ["2024-06-01T00:00", "2024-06-01T01:00"]}
    for name in ingest.HOURLY:
        hourly[name] = [0.0, 1.0]
    return {"hourly": hourly}


class FakeResponse:
    """Fausse réponse HTTP : permet de tester sans internet."""

    def __init__(self, payload=None, status=200):
        self.payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def json(self):
        return self.payload


def make_args(tmp_path, *extra):
    """Arguments de base pour main() : 2 villes, dossier temporaire, sans pause."""
    cities_file = tmp_path / "cities.csv"
    cities_file.write_text(CITIES_CSV, encoding="utf-8")
    return [
        "--cities-file", str(cities_file),
        "--out", str(tmp_path / "raw"),
        "--pause", "0",
        *extra,
    ]


# ---------------------------------------------------------------- to_frame
def test_to_frame_returns_expected_columns():
    df = ingest.to_frame(fake_payload(), "Tanger")
    assert list(df.columns) == ["city", *ingest.COLUMNS]
    assert len(df) == 2
    assert set(df["city"]) == {"Tanger"}


def test_to_frame_detects_missing_field():
    payload = fake_payload()
    del payload["hourly"]["cloud_cover"]
    with pytest.raises(ValueError, match="Schéma inattendu"):
        ingest.to_frame(payload, "Tanger")


def test_to_frame_detects_missing_hourly_block():
    with pytest.raises(ValueError, match="Schéma inattendu"):
        ingest.to_frame({}, "Tanger")


# ---------------------------------------------------------------- fetch
def test_fetch_retries_then_succeeds(monkeypatch):
    calls = []

    def fake_get(url, params, timeout):
        calls.append(1)
        if len(calls) < 3:
            raise requests.ConnectionError("réseau coupé")
        return FakeResponse(fake_payload())

    monkeypatch.setattr(ingest.requests, "get", fake_get)
    monkeypatch.setattr(ingest.time, "sleep", lambda seconds: None)
    result = ingest.fetch(35.0, -4.0, "2024-06-01", "2024-06-02")
    assert len(calls) == 3
    assert result == fake_payload()


def test_fetch_gives_up_after_all_retries(monkeypatch):
    calls = []

    def fake_get(url, params, timeout):
        calls.append(1)
        raise requests.ConnectionError("réseau coupé")

    monkeypatch.setattr(ingest.requests, "get", fake_get)
    monkeypatch.setattr(ingest.time, "sleep", lambda seconds: None)
    with pytest.raises(requests.ConnectionError):
        ingest.fetch(35.0, -4.0, "2024-06-01", "2024-06-02", retries=3)
    assert len(calls) == 3


def test_fetch_does_not_retry_client_error(monkeypatch):
    calls = []

    def fake_get(url, params, timeout):
        calls.append(1)
        return FakeResponse(status=400)

    monkeypatch.setattr(ingest.requests, "get", fake_get)
    monkeypatch.setattr(ingest.time, "sleep", lambda seconds: None)
    with pytest.raises(requests.HTTPError):
        ingest.fetch(35.0, -4.0, "2024-06-01", "2024-06-02")
    assert len(calls) == 1


# ---------------------------------------------------------------- périodes
def test_year_ranges_full_and_partial_year():
    assert ingest.year_ranges(2023, "2024-06-30") == [
        (2023, "2023-01-01", "2023-12-31"),
        (2024, "2024-01-01", "2024-06-30"),
    ]


def test_year_ranges_default_window_is_ten_years():
    ranges = ingest.year_ranges(
        ingest.DEFAULT_START_YEAR, ingest.DEFAULT_END_DATE
    )
    assert len(ranges) == 10
    assert ranges[0][0] == 2015
    assert ranges[-1] == (2024, "2024-01-01", "2024-12-31")


def test_year_ranges_empty_when_start_after_end():
    assert ingest.year_ranges(2030, "2024-12-31") == []


# ---------------------------------------------------------------- fichiers
def test_write_parquet_is_idempotent(tmp_path):
    df = ingest.to_frame(fake_payload(), "Al Hoceima")
    first = ingest.write_parquet(df, tmp_path, "Al Hoceima", 2024)
    second = ingest.write_parquet(df, tmp_path, "Al Hoceima", 2024)
    assert first == second
    assert first.name == "2024.parquet"
    files = list(tmp_path.rglob("*.parquet"))
    assert len(files) == 1
    assert len(pd.read_parquet(files[0])) == 2
    assert not list(tmp_path.rglob("*.tmp"))


def test_load_cities_reads_csv(tmp_path):
    cities_file = tmp_path / "cities.csv"
    cities_file.write_text(CITIES_CSV, encoding="utf-8")
    cities = ingest.load_cities(cities_file)
    assert [c["city"] for c in cities] == ["Tanger", "Al Hoceima"]
    assert cities[0]["latitude"] == "35.7595"


# ---------------------------------------------------------------- bout en bout
def test_main_writes_one_file_per_city_and_year(monkeypatch, tmp_path):
    monkeypatch.setattr(ingest, "fetch", lambda *args, **kwargs: fake_payload())
    args = make_args(tmp_path, "--start-year", "2023", "--end-date", "2024-12-31")
    ingest.main(args)
    files = sorted(
        f"{p.parent.name}/{p.name}" for p in (tmp_path / "raw").rglob("*.parquet")
    )
    assert files == [
        "Al_Hoceima/2023.parquet",
        "Al_Hoceima/2024.parquet",
        "Tanger/2023.parquet",
        "Tanger/2024.parquet",
    ]


def test_main_skips_complete_years_but_refreshes_partial_year(monkeypatch, tmp_path):
    calls = []

    def fake_fetch(latitude, longitude, start, end):
        calls.append((start, end))
        return fake_payload()

    monkeypatch.setattr(ingest, "fetch", fake_fetch)
    args = make_args(tmp_path, "--start-year", "2023", "--end-date", "2024-06-30")
    ingest.main(args)
    assert len(calls) == 4  # 2 villes x 2 années
    calls.clear()
    ingest.main(args)
    # 2023 est complète et déjà présente : ignorée.
    # 2024 est partielle (elle s'arrête au 30 juin) : retéléchargée.
    assert calls == [("2024-01-01", "2024-06-30")] * 2


def test_main_force_redownloads_everything(monkeypatch, tmp_path):
    calls = []

    def fake_fetch(latitude, longitude, start, end):
        calls.append((start, end))
        return fake_payload()

    monkeypatch.setattr(ingest, "fetch", fake_fetch)
    args = make_args(tmp_path, "--start-year", "2023", "--end-date", "2024-12-31")
    ingest.main(args)
    calls.clear()
    ingest.main([*args, "--force"])
    assert len(calls) == 4


def test_main_only_selected_cities(monkeypatch, tmp_path):
    monkeypatch.setattr(ingest, "fetch", lambda *args, **kwargs: fake_payload())
    args = make_args(
        tmp_path, "--start-year", "2024", "--end-date", "2024-12-31",
        "--cities", "Tanger",
    )
    ingest.main(args)
    folders = {p.parent.name for p in (tmp_path / "raw").rglob("*.parquet")}
    assert folders == {"Tanger"}