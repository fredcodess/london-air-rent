import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

SITE_CODE = "BX2"
SPECIES_CODE = "NO2"
START_DATE = "2024-01-01"
END_DATE = "2024-01-03"

API_URL = (
    "https://api.erg.ic.ac.uk/AirQuality/Data/SiteSpecies/"
    f"SiteCode={SITE_CODE}/SpeciesCode={SPECIES_CODE}/"
    f"StartDate={START_DATE}/EndDate={END_DATE}/Json"
)


def fetch_sample_measurements() -> dict:
    response = requests.get(API_URL, timeout=60)
    response.raise_for_status()

    payload = response.json()
    if not isinstance(payload, dict) or "RawAQData" not in payload:
        raise ValueError("Unexpected LAQN measurement response")

    return payload


def normalize_measurements(payload: dict) -> list[dict]:
    raw_data = payload.get("RawAQData")

    if not isinstance(raw_data, dict):
        raise ValueError("Missing or invalid RawAQData")

    site_code = raw_data.get("@SiteCode")
    species_code = raw_data.get("@SpeciesCode")
    measurements = raw_data.get("Data", [])

    # The API may return one record as a dict or many as a list.
    if isinstance(measurements, dict):
        measurements = [measurements]

    if not isinstance(measurements, list):
        raise ValueError("Unexpected measurement Data format")

    rows = []

    for measurement in measurements:
        timestamp_text = measurement.get("@MeasurementDateGMT")
        value_text = measurement.get("@Value")

        if not timestamp_text:
            raise ValueError("Measurement is missing timestamp")

        # LAQN can return an empty string for missing readings.
        # Skip these rows rather than failing the entire load.
        if value_text is None or not str(value_text).strip():
            continue

        timestamp = datetime.strptime(
            timestamp_text, "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=timezone.utc)

        try:
            value = float(value_text)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Measurement value is not numeric: {value_text!r}"
            ) from exc

        rows.append({
            "site_code": site_code,
            "species_code": species_code,
            "measurement_timestamp_utc": timestamp.isoformat(),
            "value": value,
        })

    return rows


def save_measurements_csv(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["site_code", "species_code", "measurement_timestamp_utc", "value",]

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    payload = fetch_sample_measurements()

    raw_path = Path(
        f"data/raw/sample_{SITE_CODE}_{SPECIES_CODE}_"
        f"{START_DATE}_{END_DATE}.json"
    )
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    with raw_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)

    rows = normalize_measurements(payload)

    csv_path = Path("data/processed/sample_measurements.csv")
    save_measurements_csv(rows, csv_path)

    print(f"Raw response saved to: {raw_path}")
    print(f"Normalized measurements: {len(rows)}")
    print(f"Normalized CSV saved to: {csv_path}")
    print("First normalized row:", rows[0] if rows else "No rows")


if __name__ == "__main__":
    main()