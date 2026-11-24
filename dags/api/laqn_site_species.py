import csv
import json
from pathlib import Path

import requests

API_URL = (
    "https://api.erg.ic.ac.uk/AirQuality/Information/"
    "MonitoringSiteSpecies/GroupName=London/Json"
)


def fetch_site_species_metadata() -> dict:
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()

    payload = response.json()
    if not isinstance(payload, dict) or "Sites" not in payload:
        raise ValueError("Unexpected LAQN site-species response")

    return payload


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def get_field(record: dict, *names):
    for name in names:
        if name in record:
            return record[name]
    return None


def normalize_metadata(payload: dict) -> tuple[list[dict], list[dict]]:
    sites_container = payload.get("Sites", {})
    raw_sites = as_list(sites_container.get("Site"))

    sites = []
    site_species = []

    for raw_site in raw_sites:
        site_code = get_field(raw_site, "@SiteCode", "SiteCode")
        site_name = get_field(raw_site, "@SiteName", "SiteName")

        if not site_code:
            continue

        site = {
            "site_code": str(site_code).strip(),
            "site_name": str(site_name or "").strip(),
            "local_authority": get_field(
                raw_site, "@LocalAuthorityName", "LocalAuthorityName"
            ),
            "latitude": get_field(raw_site, "@Latitude", "Latitude"),
            "longitude": get_field(raw_site, "@Longitude", "Longitude"),
            "site_type": get_field(raw_site, "@SiteType", "SiteType"),
            "date_opened": get_field(raw_site, "@DateOpened", "DateOpened"),
            "date_closed": get_field(raw_site, "@DateClosed", "DateClosed"),
        }
        sites.append(site)

        species_container = raw_site.get("Species", {})
        raw_species = as_list(
            species_container.get("Species")
            if isinstance(species_container, dict)
            else species_container
        )

        for species in raw_species:
            if not isinstance(species, dict):
                continue

            species_code = get_field(
                species, "@SpeciesCode", "SpeciesCode", "@Code", "Code"
            )
            if not species_code:
                continue

            site_species.append({
                "site_code": str(site_code).strip(),
                "species_code": str(species_code).strip(),
                "species_name": get_field(
                    species, "@SpeciesDescription", "SpeciesDescription", "@SpeciesName", "SpeciesName", "@Name", "Name",
                ),
            })

            # Remove exact duplicate site records while preserving order.
            sites = list({
                tuple(sorted(site.items())): site
                for site in sites
            }.values())

            # Each site-pollutant combination should appear only once.
            site_species = list({
                (row["site_code"], row["species_code"]): row
                for row in site_species
            }.values())

    return sites, site_species


def write_csv(rows: list[dict], output_path: Path, fieldnames: list[str]):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    payload = fetch_site_species_metadata()

    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Preserve the original API response.
    with (raw_dir / "laqn_site_species.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)

    sites, site_species = normalize_metadata(payload)

    write_csv(
        sites,
        processed_dir / "sites.csv",
        [
            "site_code", "site_name", "local_authority",
            "latitude", "longitude", "site_type",
            "date_opened", "date_closed",
        ],
    )

    write_csv(
        site_species,
        processed_dir / "site_species.csv",
        ["site_code", "species_code", "species_name"],
    )

    print(f"Sites normalized: {len(sites)}")
    print(f"Site-species pairs normalized: {len(site_species)}")


if __name__ == "__main__":
    main()