from flask import Flask, jsonify, request
from physics_engine import calculate_flight_trajectory
import pandas as pd

app = Flask(__name__)

@app.route("/api/simulate", methods=["POST"])
def run_simulation():
    data = request.json or {}
    alt = float(data.get("altitude_ft", 0))
    mach = float(data.get("velocity_mach", 1.2))
    q = float(data.get("dynamic_pressure_kpa", 15.0))
    o2 = float(data.get("oxygen_pct", 21.0))
    
    result = calculate_flight_trajectory(alt, mach, q, o2)
    return jsonify(result)

@app.route("/api/datasets", methods=["GET"])
def get_datasets():
    # Canonical NASA PSI-117 dataset records
    records = [
        {"Fuel": "n-heptane", "do_mm": 0.5, "P_atm": 1.0, "XO2": "21%", "Reference": "https://doi.org/10.1016/j.proci.2018.05.151"},
        {"Fuel": "n-dodecane", "do_mm": 4.5, "P_atm": 2.75, "XO2": "21%", "Reference": "https://doi.org/10.1016/j.proci.2018.09.015"}
    ]
    return jsonify(records)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
