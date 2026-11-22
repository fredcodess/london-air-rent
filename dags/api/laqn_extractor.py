
import json
from datetime import datetime, timezone
from pathlib import Path

import requests


API_URL = (
    "https://api.erg.ic.ac.uk/AirQuality/Information/"
    "MonitoringSites/GroupName=London/Json"
)


def fetch_site_metadata() -> dict:
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()

    payload = response.json()

    if not isinstance(payload, dict) or "Sites" not in payload:
        raise ValueError("Unexpected LAQN site metadata response")

    return payload


def save_raw_metadata(payload: dict, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"laqn_sites_{timestamp}.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)

    return output_path


def extract_site_metadata(output_dir: Path) -> Path:
    payload = fetch_site_metadata()
    return save_raw_metadata(payload, output_dir)

if __name__ == "__main__":
  extract_site_metadata(
        Path("data/raw")
    )
print(f"Saved raw site metadata to: data/raw")