import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


# --------------------------------------------------
# RCERT SMART CAMPUS DIGITAL TWIN
# Synthetic IoT Sensor Dataset Generator
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "campus_sensor_data.csv"

START_DATE = datetime(2026, 8, 1, 8, 0, 0)
TOTAL_RECORDS = 360

random.seed(42)


def generate_sensor_data():
    records = []

    for i in range(TOTAL_RECORDS):
        timestamp = START_DATE + timedelta(hours=2 * i)

        hour = timestamp.hour
        day_factor = timestamp.weekday()

        # Temperature variation
        temperature = round(
            24
            + 5 * random.random()
            + (3 if 11 <= hour <= 16 else 0)
            + random.uniform(-1.5, 1.5),
            2
        )

        # Humidity variation
        humidity = round(
            75
            - (temperature - 24) * 2
            + random.uniform(-5, 5),
            2
        )

        humidity = max(35, min(90, humidity))

        # Occupancy percentage
        if day_factor >= 5:
            occupancy = random.randint(5, 25)
        elif 9 <= hour <= 17:
            occupancy = random.randint(35, 95)
        else:
            occupancy = random.randint(10, 40)

        # Electricity consumption
        electricity = round(
            5
            + occupancy * 0.12
            + random.uniform(0, 8),
            2
        )

        # Water consumption
        water = round(
            15
            + occupancy * 0.45
            + random.uniform(0, 15),
            2
        )

        records.append([
            timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            temperature,
            humidity,
            electricity,
            water,
            occupancy
        ])

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow([
            "timestamp",
            "temperature",
            "humidity",
            "electricity",
            "water",
            "occupancy"
        ])

        writer.writerows(records)

    print("Dataset generated successfully!")
    print(f"Total records: {len(records)}")
    print(f"File saved at: {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_sensor_data()