from flask import Flask, render_template, jsonify, request
import sqlite3
import pandas as pd
import joblib
from pathlib import Path
from datetime import datetime
import random

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent

DATABASE = BASE_DIR / "database" / "campus.db"
DATASET = BASE_DIR / "dataset" / "campus_sensor_data.csv"

OCCUPANCY_MODEL = BASE_DIR / "models" / "occupancy_model.pkl"
ENERGY_MODEL = BASE_DIR / "models" / "energy_model.pkl"


# ============================================================
# CAMPUS ZONES
# ============================================================

CAMPUS_ZONES = [
    {"id": "boys_hostel", "name": "Boys Hostel", "type": "Hostel"},
    {"id": "mba", "name": "MBA", "type": "Academic"},
    {"id": "polytechnic", "name": "Polytechnic", "type": "Academic"},
    {"id": "mining", "name": "Mining Department", "type": "Academic"},
    {"id": "computer_science", "name": "Computer Science", "type": "Academic"},
    {"id": "civil", "name": "Civil Department", "type": "Academic"},
    {"id": "data_science", "name": "Data Science", "type": "Academic"},
    {"id": "mechanical", "name": "Mechanical Department", "type": "Academic"},
    {"id": "electrical", "name": "Electrical Department", "type": "Academic"},
    {"id": "electrical_workshop", "name": "Electrical Workshop", "type": "Workshop"},
    {"id": "auditorium", "name": "Auditorium", "type": "Facility"},
    {"id": "canteen", "name": "Canteen", "type": "Facility"},
    {"id": "gym", "name": "Gym", "type": "Facility"},
    {"id": "girls_hostel", "name": "Girls Hostel", "type": "Hostel"},
    {"id": "boys_parking", "name": "Boys Parking", "type": "Parking"},
    {"id": "girls_parking", "name": "Girls Parking", "type": "Parking"},
    {"id": "main_building", "name": "RCERT Main Building", "type": "Administration"},
    {"id": "main_gate", "name": "Main Gate", "type": "Entrance"}
]


# ============================================================
# DATABASE
# ============================================================

def get_connection():

    DATABASE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():

    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS sensor_readings (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            timestamp TEXT NOT NULL,

            temperature REAL NOT NULL,

            humidity REAL NOT NULL,

            electricity REAL NOT NULL,

            water REAL NOT NULL,

            occupancy REAL NOT NULL,

            source TEXT DEFAULT 'simulation'

        )
    """)

    connection.commit()

    connection.close()


# ============================================================
# SIMULATED SENSOR
# ============================================================

def generate_simulated_reading():

    hour = datetime.now().hour

    if 9 <= hour <= 17:

        occupancy = random.randint(
            35,
            92
        )

    else:

        occupancy = random.randint(
            10,
            40
        )


    temperature = round(
        random.uniform(
            25,
            34
        ),
        2
    )


    humidity = round(
        random.uniform(
            45,
            78
        ),
        2
    )


    electricity = round(
        5
        + occupancy * 0.12
        + random.uniform(0, 5),
        2
    )


    water = round(
        15
        + occupancy * 0.45
        + random.uniform(0, 10),
        2
    )


    return {

        "timestamp":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "temperature":
            temperature,

        "humidity":
            humidity,

        "electricity":
            electricity,

        "water":
            water,

        "occupancy":
            occupancy,

        "source":
            "simulation"
    }


# ============================================================
# SAVE DATA
# ============================================================

def save_sensor_reading(reading):

    connection = get_connection()

    connection.execute("""
        INSERT INTO sensor_readings
        (
            timestamp,
            temperature,
            humidity,
            electricity,
            water,
            occupancy,
            source
        )

        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (

        reading["timestamp"],
        reading["temperature"],
        reading["humidity"],
        reading["electricity"],
        reading["water"],
        reading["occupancy"],
        reading.get(
            "source",
            "simulation"
        )

    ))

    connection.commit()

    connection.close()


# ============================================================
# LATEST DATA
# ============================================================

def get_latest_reading():

    connection = get_connection()

    row = connection.execute("""
        SELECT *
        FROM sensor_readings
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()

    connection.close()


    if row:

        return dict(row)


    reading = generate_simulated_reading()

    save_sensor_reading(
        reading
    )

    return reading


# ============================================================
# ML OCCUPANCY
# ============================================================

def predict_occupancy(reading):

    try:

        if not OCCUPANCY_MODEL.exists():
            return None


        model = joblib.load(
            OCCUPANCY_MODEL
        )


        features = [[

            reading["temperature"],

            reading["humidity"],

            reading["electricity"],

            reading["water"]

        ]]


        prediction = model.predict(
            features
        )[0]


        return round(
            max(
                0,
                min(
                    100,
                    prediction
                )
            ),
            2
        )


    except Exception:

        return None


# ============================================================
# ML ENERGY
# ============================================================

def predict_energy(reading):

    try:

        if not ENERGY_MODEL.exists():
            return None


        model = joblib.load(
            ENERGY_MODEL
        )


        features = [[

            reading["temperature"],

            reading["humidity"],

            reading["occupancy"],

            reading["water"]

        ]]


        prediction = model.predict(
            features
        )[0]


        return round(
            max(
                0,
                prediction
            ),
            2
        )


    except Exception:

        return None


# ============================================================
# STATUS + ALERTS
# ============================================================

def get_status(reading):

    alerts = []


    if reading["temperature"] >= 35:

        alerts.append({
            "level": "critical",
            "message":
                "Critical temperature detected"
        })

    elif reading["temperature"] >= 32:

        alerts.append({
            "level": "warning",
            "message":
                "Temperature is above normal"
        })


    if reading["humidity"] >= 80:

        alerts.append({
            "level": "warning",
            "message":
                "High humidity detected"
        })


    if reading["occupancy"] >= 85:

        alerts.append({
            "level": "warning",
            "message":
                "High campus occupancy detected"
        })


    if reading["electricity"] >= 18:

        alerts.append({
            "level": "warning",
            "message":
                "High electricity consumption"
        })


    if any(
        alert["level"] == "critical"
        for alert in alerts
    ):

        status = "Critical"

    elif alerts:

        status = "Warning"

    else:

        status = "Normal"


    return status, alerts


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# LATEST DATA API
# ============================================================

@app.route("/api/latest-data")
def latest_data():

    reading = get_latest_reading()


    occupancy_prediction = \
        predict_occupancy(
            reading
        )


    energy_prediction = \
        predict_energy(
            reading
        )


    status, alerts = \
        get_status(
            reading
        )


    return jsonify({

        "success": True,

        "data": reading,

        "predictions": {

            "occupancy":
                occupancy_prediction,

            "energy":
                energy_prediction

        },

        "status":
            status,

        "alerts":
            alerts

    })


# ============================================================
# GENERATE NEW READING
# ============================================================

@app.route(
    "/api/simulate-reading",
    methods=["POST"]
)
def simulate_reading():

    reading = \
        generate_simulated_reading()


    save_sensor_reading(
        reading
    )


    return jsonify({

        "success": True,

        "message":
            "New sensor reading generated",

        "data":
            reading

    })


# ============================================================
# IOT API
# ============================================================

@app.route(
    "/api/iot-data",
    methods=["POST"]
)
def receive_iot_data():

    data = request.get_json(
        silent=True
    )


    if not data:

        return jsonify({

            "success": False,

            "message":
                "No JSON data received"

        }), 400


    required = [

        "temperature",

        "humidity"

    ]


    for field in required:

        if field not in data:

            return jsonify({

                "success": False,

                "message":
                    f"Missing field: {field}"

            }), 400


    try:

        reading = {

            "timestamp":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            "temperature":
                float(
                    data["temperature"]
                ),

            "humidity":
                float(
                    data["humidity"]
                ),

            "electricity":
                float(
                    data.get(
                        "electricity",
                        0
                    )
                ),

            "water":
                float(
                    data.get(
                        "water",
                        0
                    )
                ),

            "occupancy":
                float(
                    data.get(
                        "occupancy",
                        0
                    )
                ),

            "source":
                "ESP32_IoT"

        }


        save_sensor_reading(
            reading
        )


        return jsonify({

            "success": True,

            "message":
                "IoT data received successfully",

            "data":
                reading

        })


    except ValueError:

        return jsonify({

            "success": False,

            "message":
                "Invalid sensor values"

        }), 400


# ============================================================
# CAMPUS ZONES
# ============================================================

@app.route("/api/campus-zones")
def campus_zones():

    return jsonify({

        "success": True,

        "zones":
            CAMPUS_ZONES

    })


# ============================================================
# HISTORY
# ============================================================

@app.route("/api/history")
def history():

    connection = get_connection()


    rows = connection.execute("""
        SELECT
            timestamp,
            temperature,
            humidity,
            electricity,
            water,
            occupancy,
            source
        FROM sensor_readings
        ORDER BY id DESC
        LIMIT 50
    """).fetchall()


    connection.close()


    return jsonify({

        "success": True,

        "data":
            [
                dict(row)
                for row in rows
            ]

    })


# ============================================================
# ANALYTICS SUMMARY
# ============================================================

@app.route("/api/analytics")
def analytics():

    connection = get_connection()


    rows = connection.execute("""
        SELECT
            timestamp,
            temperature,
            humidity,
            electricity,
            water,
            occupancy
        FROM sensor_readings
        ORDER BY id ASC
        LIMIT 100
    """).fetchall()


    connection.close()


    records = [
        dict(row)
        for row in rows
    ]


    if not records:

        return jsonify({

            "success": True,

            "data": []

        })


    return jsonify({

        "success": True,

        "data": records

    })


# ============================================================
# SYSTEM SUMMARY
# ============================================================

@app.route("/api/system-summary")
def system_summary():

    reading = get_latest_reading()

    status, alerts = \
        get_status(reading)


    critical = sum(

        1

        for alert in alerts

        if alert["level"]
        == "critical"

    )


    warning = sum(

        1

        for alert in alerts

        if alert["level"]
        == "warning"

    )


    return jsonify({

        "success": True,

        "total_zones":
            len(CAMPUS_ZONES),

        "overall_status":
            status,

        "normal":
            len(CAMPUS_ZONES)
            - warning
            - critical,

        "warning":
            warning,

        "critical":
            critical

    })


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    initialize_database()


    print("=" * 60)

    print(
        "RCERT SMART CAMPUS DIGITAL TWIN"
    )

    print("=" * 60)

    print(
        "Dashboard: http://127.0.0.1:5000"
    )

    print(
        "IoT API: http://127.0.0.1:5000/api/iot-data"
    )

    print(
        "Analytics: http://127.0.0.1:5000/api/analytics"
    )

    print("=" * 60)


    app.run(

        host="0.0.0.0",

        port=5000,

        debug=True

    )