import pandas as pd
import joblib
from pathlib import Path

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score


# --------------------------------------------------
# RCERT SMART CAMPUS DIGITAL TWIN
# Machine Learning Model Training
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR.parent / "dataset" / "campus_sensor_data.csv"


# Load dataset
data = pd.read_csv(DATA_FILE)

print("Dataset loaded successfully!")
print(f"Total records: {len(data)}")


# --------------------------------------------------
# OCCUPANCY PREDICTION MODEL
# --------------------------------------------------

occupancy_features = [
    "temperature",
    "humidity",
    "electricity",
    "water"
]

X_occupancy = data[occupancy_features]
y_occupancy = data["occupancy"]

X_train, X_test, y_train, y_test = train_test_split(
    X_occupancy,
    y_occupancy,
    test_size=0.20,
    random_state=42
)

occupancy_model = RandomForestRegressor(
    n_estimators=150,
    random_state=42
)

occupancy_model.fit(X_train, y_train)

occupancy_predictions = occupancy_model.predict(X_test)

occupancy_mae = mean_absolute_error(
    y_test,
    occupancy_predictions
)

occupancy_r2 = r2_score(
    y_test,
    occupancy_predictions
)

occupancy_model_file = BASE_DIR / "occupancy_model.pkl"

joblib.dump(
    occupancy_model,
    occupancy_model_file
)


# --------------------------------------------------
# ENERGY PREDICTION MODEL
# --------------------------------------------------

energy_features = [
    "temperature",
    "humidity",
    "occupancy",
    "water"
]

X_energy = data[energy_features]
y_energy = data["electricity"]

X_train, X_test, y_train, y_test = train_test_split(
    X_energy,
    y_energy,
    test_size=0.20,
    random_state=42
)

energy_model = RandomForestRegressor(
    n_estimators=150,
    random_state=42
)

energy_model.fit(X_train, y_train)

energy_predictions = energy_model.predict(X_test)

energy_mae = mean_absolute_error(
    y_test,
    energy_predictions
)

energy_r2 = r2_score(
    y_test,
    energy_predictions
)

energy_model_file = BASE_DIR / "energy_model.pkl"

joblib.dump(
    energy_model,
    energy_model_file
)


# --------------------------------------------------
# RESULTS
# --------------------------------------------------

print("\n========================================")
print("      RCERT SMART CAMPUS ML RESULTS")
print("========================================")

print("\nOccupancy Prediction Model")
print(f"MAE : {occupancy_mae:.2f}")
print(f"R2  : {occupancy_r2:.2f}")
print(f"Model saved: {occupancy_model_file}")

print("\nEnergy Consumption Model")
print(f"MAE : {energy_mae:.2f}")
print(f"R2  : {energy_r2:.2f}")
print(f"Model saved: {energy_model_file}")

print("\nML models trained successfully!")