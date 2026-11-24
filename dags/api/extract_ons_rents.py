import csv
from pathlib import Path
from openpyxl import load_workbook

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = (PROJECT_ROOT/ "data"/ "raw"/ "ons_private_rents_2026-11.xlsx")
OUTPUT_FILE = (PROJECT_ROOT/ "data"/ "processed"/ "ons_private_rents.csv")


def main():
    workbook = load_workbook(INPUT_FILE, read_only=True, data_only=True,)

    worksheet = workbook["Table 1"]

    headers = [cell.value for cell in worksheet[3]]

    column_index = {
        name: index
        for index, name in enumerate(headers)
    }

    required_columns = [
        "Time period",
        "Area code",
        "Area name",
        "Region or country name",
        "Rental price",
    ]

    for column in required_columns:
        if column not in column_index:
            raise ValueError(
                f"Missing required column: {column}"
            )

    output_rows = []

    for row in worksheet.iter_rows(min_row=4, values_only=True,):
        region = row[column_index["Region or country name"]]

        if region != "London":
            continue

        month = row[column_index["Time period"]]
        borough_code = row[column_index["Area code"]]
        borough_name = row[column_index["Area name"]]
        rent = row[column_index["Rental price"]]

        if not all([month, borough_code, borough_name]):
            raise ValueError("A London row has missing identifying data.")

        if not isinstance(rent, (int, float)) or rent <= 0:
            raise ValueError(f"Invalid rent value for {borough_name}: {rent}")

        output_rows.append({
            "month": month.strftime("%Y-%m-%d"),
            "borough_code": borough_code,
            "borough_name": borough_name,
            "rent_gbp": rent,
        })

    # Check that each borough has only one row per month.
    keys = [
        (row["month"], row["borough_code"])
        for row in output_rows
    ]

    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate borough-month records found.")

    borough_count = len({
        row["borough_code"]
        for row in output_rows
    })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True,)

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8",) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "month",
                "borough_code",
                "borough_name",
                "rent_gbp",
            ],
        )

        writer.writeheader()
        writer.writerows(output_rows)

    workbook.close()

    print(f"Output file: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()