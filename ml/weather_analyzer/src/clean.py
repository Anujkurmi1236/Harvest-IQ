import csv
from pathlib import Path

# input_csv = Path(
#     "/home/anuj/Desktop/projects/harvest-iq/ml/weather_analyzer/data/Climate_change_Emissions_indicators_E_All_Data_(Normalized)/Climate_change_Emissions_indicators_E_All_Data_(Normalized).csv"
# )
# output_dir = Path(
#     "/home/anuj/Desktop/projects/harvest-iq/ml/weather_analyzer/data/req_data"
# )
# output_csv = output_dir / "india_climate_data.csv"

# input_csv = Path(
#     "ml/weather_analyzer/data/Environment_LandCover_E_All_Data_(Normalized)/Environment_LandCover_E_All_Data_(Normalized).csv"
# )
# output_dir = Path(
#     "ml/weather_analyzer/data/req_data"
# )
# output_csv = output_dir / "env_land_coverf.csv"

input_csv = Path(
    "ml/weather_analyzer/data/Environment_LandUse_E_All_Data_(Normalized)/Environment_LandUse_E_All_Data_(Normalized).csv"
)
output_dir = Path(
    "ml/weather_analyzer/data/req_data"
)
output_csv = output_dir / "env_land_use.csv"

output_dir.mkdir(parents=True, exist_ok=True)

rows_written = 0

encodings_to_try = ("utf-8", "latin-1")
last_decode_error = None

for encoding in encodings_to_try:
    rows_written = 0
    try:
        with input_csv.open("r", encoding=encoding, newline="") as infile, \
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
        break
    except UnicodeDecodeError as exc:
        last_decode_error = exc
else:
    if last_decode_error is None:
        raise RuntimeError(f"Failed to read input CSV with encodings: {', '.join(encodings_to_try)}")

    raise UnicodeDecodeError(
        last_decode_error.encoding,
        last_decode_error.object,
        last_decode_error.start,
        last_decode_error.end,
        f"{last_decode_error.reason}. Tried encodings: {', '.join(encodings_to_try)}",
    )

print(f"Saved {rows_written} India-specific rows to: {output_csv}")