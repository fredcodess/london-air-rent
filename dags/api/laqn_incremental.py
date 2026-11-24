import csv
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from laqn_measurements_sample import normalize_measurements


API_BASE_URL = (
    "https://api.erg.ic.ac.uk/AirQuality/Data/SiteSpecies/"
)

DATA_DIR = Path("data")
INITIAL_START_DATE = "2024-01-01"
LOOKBACK_DAYS = 3
CHUNK_DAYS = 14

CSV_FIELDS = ["site_code", "species_code", "measurement_timestamp_utc", "value",]


def fetch_measurements(site_code: str, species_code: str, start_date: str, end_date: str,) -> dict:
    url = (
        f"{API_BASE_URL}SiteCode={site_code}/"
        f"SpeciesCode={species_code}/"
        f"StartDate={start_date}/"
        f"EndDate={end_date}/Json"
    )

    response = requests.get(url, timeout=(10, 180))
    response.raise_for_status()

    payload = response.json()
    if not isinstance(payload, dict) or "RawAQData" not in payload:
        raise ValueError("Unexpected LAQN measurement response")

    return payload


def load_watermarks(path: Path) -> dict:
    if not path.exists():
        return {}

    with path.open(encoding="utf-8") as file:
        return json.load(file)


def calculate_start_date(watermark: str | None, initial_start_date: str, lookback_days: int = LOOKBACK_DAYS,) -> str:
    if not watermark:
        return initial_start_date

    watermark_date = datetime.fromisoformat(watermark).date()
    start_date = watermark_date - timedelta(days=lookback_days)
    return start_date.isoformat()


def merge_measurements(existing_rows: list[dict], new_rows: list[dict],) -> list[dict]:
    merged = {}

    for row in existing_rows + new_rows:
        key = (
            row["site_code"],
            row["species_code"],
            row["measurement_timestamp_utc"],
        )
        # New rows replace existing rows with the same natural key.
        merged[key] = row

    return sorted(
        merged.values(),
        key=lambda row: row["measurement_timestamp_utc"],
    )


def read_measurements(path: Path) -> list[dict]:
    if not path.exists():
        return []

    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_measurements(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    with temporary_path.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    temporary_path.replace(path)


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    temporary_path.replace(path)


def run_incremental(
    site_code: str,
    species_code: str,
    initial_start_date: str = INITIAL_START_DATE,
    data_dir: Path = DATA_DIR,
    end_date: str | None = None,
    lookback_days: int = LOOKBACK_DAYS,
) -> int:
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    state_dir = data_dir / "state"

    watermark_path = state_dir / "watermarks.json"
    output_path = processed_dir / (
        f"measurements_{site_code}_{species_code}.csv"
    )

    watermarks = load_watermarks(watermark_path)
    pair_key = f"{site_code}|{species_code}"
    previous_watermark = watermarks.get(pair_key)

    start_date = calculate_start_date(
        previous_watermark,
        initial_start_date,
        lookback_days,
    )

    if end_date is None:
        end_date = datetime.now(timezone.utc).date().isoformat()

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    if start > end:
        raise ValueError("Start date must not be after end date")

    existing_rows = read_measurements(output_path)
    total_new_rows = 0
    current_date = start

    while current_date <= end:
        chunk_end = min(
            current_date + timedelta(days=CHUNK_DAYS - 1),
            end,
        )

        chunk_start_text = current_date.isoformat()
        chunk_end_text = chunk_end.isoformat()

        print(
            f"Fetching {pair_key}: "
            f"{chunk_start_text} to {chunk_end_text}"
        )

        # 1. Fetch one chunk
        payload = fetch_measurements(
            site_code,
            species_code,
            chunk_start_text,
            chunk_end_text,
        )

        # 2. Save the raw API response
        raw_dir.mkdir(parents=True, exist_ok=True)

        raw_path = raw_dir / (
            f"laqn_{site_code}_{species_code}_"
            f"{chunk_start_text}_{chunk_end_text}.json"
        )

        with raw_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)

        # 3. Normalize and merge
        new_rows = normalize_measurements(payload)

        merged_rows = merge_measurements(
            existing_rows,
            new_rows,
        )

        # 4. Write data before advancing the watermark
        write_measurements(output_path, merged_rows)

        # Update in-memory rows for the next chunk
        existing_rows = merged_rows
        total_new_rows += len(new_rows)

        # 5. Mark this chunk as successfully processed
        watermarks[pair_key] = (
            f"{chunk_end_text}T23:59:59+00:00"
        )

        write_json_atomic(watermark_path, watermarks)

        print(f"Rows fetched in chunk: {len(new_rows)}")
        print(f"Rows in output: {len(existing_rows)}")
        print(f"Watermark: {watermarks[pair_key]}")

        # Move to the next chunk
        current_date = chunk_end + timedelta(days=1)

    print(f"Completed pair: {pair_key}")
    print(f"Total new rows fetched: {total_new_rows}")
    print(f"Total rows in output: {len(existing_rows)}")

    return total_new_rows


if __name__ == "__main__":
    run_incremental(
        site_code="BX2",
        species_code="NO2",
    )