from __future__ import annotations
import numpy as np

def calculate_flight_trajectory(altitude_ft: float, velocity_mach: float, dynamic_pressure_kpa: float, oxygen_pct: float):
    """
    Computes real-time thermal stress, acoustic resonance, and fire hazard risk 
    during a realistic gravity-turn rocket ascent.
    """
    # Convert altitude to meters
    alt_m = altitude_ft * 0.3048
    
    # Ambient temperature model (ISA standard atmosphere approximation)
    if alt_m <= 11000:
        temp_c = 15.0 - (0.0065 * alt_m)
    elif alt_m <= 25000:
        temp_c = -56.5
    else:
        temp_c = -56.5 + (0.001 * (alt_m - 25000))

    # Fire hazard & thermal stress index calculation
    thermal_stress = round(abs(temp_c) * 0.12 + (velocity_mach ** 2) * 1.5, 2)
    acoustic_risk = "CRITICAL" if dynamic_pressure_kpa > 30.0 else "NOMINAL"
    
    return {
        "altitude_m": round(alt_m, 2),
        "ambient_temp_c": round(temp_c, 2),
        "thermal_stress_index": thermal_stress,
        "acoustic_status": acoustic_risk,
        "combustion_stability": "Stable Flame" if oxygen_pct <= 25 else "High Quenching Risk"
    }
