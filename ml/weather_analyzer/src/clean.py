import csv
from pathlib import Path

input_csv = Path(
    "/home/anuj/Desktop/projects/harvest-iq/ml/weather_analyzer/data/Climate_change_Emissions_indicators_E_All_Data_(Normalized)/Climate_change_Emissions_indicators_E_All_Data_(Normalized).csv"
)
output_dir = Path(
    "/home/anuj/Desktop/projects/harvest-iq/ml/weather_analyzer/data/req_data"
)
output_csv = output_dir / "india_climate_data.csv"

output_dir.mkdir(parents=True, exist_ok=True)

rows_written = 0
with input_csv.open("r", encoding="utf-8", newline="") as infile, \
     output_csv.open("w", encoding="utf-8", newline="") as outfile:

    reader = csv.DictReader(infile)
    fieldnames = reader.fieldnames
    if fieldnames is None:
        raise ValueError("Input CSV is missing a header row.")

    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        area = (row.get("Area") or "").strip().lower()
        m49 = (row.get("Area Code (M49)") or "").replace("'", "").strip()

        if area == "india" or m49 == "356":
            writer.writerow(row)
            rows_written += 1

print(f"Saved {rows_written} India-specific rows to: {output_csv}")