import csv
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_FILE = (PROJECT_ROOT/ "data"/ "processed"/ "ons_private_rents.csv")

load_dotenv(PROJECT_ROOT / ".env")


def main():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is missing from .env")

    with CSV_FILE.open("r", newline="", encoding="utf-8",) as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    if not rows:
        raise ValueError("Rent CSV contains no data.")

    print(f"Read {len(rows):,} rent records from CSV.")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:

            cursor.execute("TRUNCATE TABLE staging.rent_monthly")

            cursor.executemany(
                """
                INSERT INTO staging.rent_monthly (
                    month,
                    borough_code,
                    borough_name,
                    rent_gbp
                )
                VALUES (%s, %s, %s, %s)
                """,
                [
                    (
                        row["month"],
                        row["borough_code"],
                        row["borough_name"],
                        row["rent_gbp"],
                    )
                    for row in rows
                ],
            )

            # borough dimension records.
            cursor.execute(
                """
                INSERT INTO core.dim_borough (
                    borough_code,
                    borough_name
                )
                SELECT DISTINCT
                    borough_code,
                    borough_name
                FROM staging.rent_monthly
                ON CONFLICT (borough_code)
                DO UPDATE SET
                    borough_name = EXCLUDED.borough_name
                """
            )

            # borough-month rent facts.
            cursor.execute(
                """
                INSERT INTO core.fact_rent (
                    borough_code,
                    month,
                    rent_gbp
                )
                SELECT
                    borough_code,
                    month,
                    rent_gbp
                FROM staging.rent_monthly
                ON CONFLICT (borough_code, month)
                DO UPDATE SET
                    rent_gbp = EXCLUDED.rent_gbp,
                    loaded_at = NOW()
                """
            )

    print("Rent load completed successfully.")


if __name__ == "__main__":
    main()