import csv
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT_ROOT / "data" / "processed" / "measurements_BX2_NO2.csv"


def load_csv(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def load_to_postgres(rows: list[dict]) -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is missing from .env")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            # Refresh staging for this CSV load.
            cur.execute("DELETE FROM staging.air_quality_measurements")

            cur.executemany(
                """
                INSERT INTO staging.air_quality_measurements (
                    site_code,
                    species_code,
                    measurement_timestamp_utc,
                    value
                )
                VALUES (%s, %s, %s, %s)
                """,
                [
                    (
                        row["site_code"],
                        row["species_code"],
                        row["measurement_timestamp_utc"],
                        float(row["value"]) if row["value"].strip() else None,
                    )
                    for row in rows
                ],
            )

            # Ensure dimension keys exist before inserting facts.
            cur.execute(
                """
                INSERT INTO core.dim_site (site_code)
                SELECT DISTINCT site_code
                FROM staging.air_quality_measurements
                ON CONFLICT (site_code) DO NOTHING
                """
            )

            cur.execute(
                """
                INSERT INTO core.dim_species (species_code)
                SELECT DISTINCT species_code
                FROM staging.air_quality_measurements
                ON CONFLICT (species_code) DO NOTHING
                """
            )

            # Upsert facts: rerunning the loader won't duplicate measurements.
            cur.execute(
                """
                INSERT INTO core.fact_air_quality (
                    site_code,
                    species_code,
                    measurement_timestamp_utc,
                    value
                )
                SELECT
                    site_code,
                    species_code,
                    measurement_timestamp_utc,
                    value
                FROM staging.air_quality_measurements
                ON CONFLICT (
                    site_code,
                    species_code,
                    measurement_timestamp_utc
                )
                DO UPDATE SET
                    value = EXCLUDED.value,
                    loaded_at = NOW()
                """
            )

    return len(rows)


if __name__ == "__main__":
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Measurement CSV not found: {CSV_PATH}")

    records = load_csv(CSV_PATH)
    loaded = load_to_postgres(records)

    print(f"Loaded {loaded:,} rows into staging and upserted into core.")