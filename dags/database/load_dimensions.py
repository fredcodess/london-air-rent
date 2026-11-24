import csv
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SITES_CSV = PROJECT_ROOT / "data" / "processed" / "sites.csv"
SITE_SPECIES_CSV = PROJECT_ROOT / "data" / "processed" / "site_species.csv"


def read_csv(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def load_dimensions() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is missing from .env")

    sites = read_csv(SITES_CSV)
    site_species = read_csv(SITE_SPECIES_CSV)

    # Build one record per species code and check names are consistent.
    species_by_code = {}

    for row in site_species:
        code = row["species_code"].strip()
        name = row["species_name"].strip()

        if not code or not name:
            continue

        if code in species_by_code and species_by_code[code] != name:
            raise ValueError(
                f"Conflicting names for species {code}: "
                f"{species_by_code[code]} / {name}"
            )

        species_by_code[code] = name

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO core.dim_site (
                    site_code,
                    site_name,
                    latitude,
                    longitude,
                    borough_name,
                    site_type,
                    date_opened,
                    date_closed
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (site_code)
                DO UPDATE SET
                    site_name = EXCLUDED.site_name,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    borough_name = EXCLUDED.borough_name,
                    site_type = EXCLUDED.site_type,
                    date_opened = EXCLUDED.date_opened,
                    date_closed = EXCLUDED.date_closed
                """,
                [
                    (
                        row["site_code"].strip(),
                        row["site_name"].strip() or None,
                        float(row["latitude"]) if row["latitude"].strip() else None,
                        float(row["longitude"]) if row["longitude"].strip() else None,
                        row["local_authority"].strip() or None,
                        row["site_type"].strip() or None,
                        row["date_opened"].strip() or None,
                        row["date_closed"].strip() or None,
                    )
                    for row in sites
                ],
            )

            cur.executemany(
                """
                INSERT INTO core.dim_species (species_code, species_name)
                VALUES (%s, %s)
                ON CONFLICT (species_code)
                DO UPDATE SET species_name = EXCLUDED.species_name
                """,
                list(species_by_code.items()),
            )

    print(f"Upserted {len(sites)} site records.")
    print(f"Upserted {len(species_by_code)} species records.")


if __name__ == "__main__":
    load_dimensions()