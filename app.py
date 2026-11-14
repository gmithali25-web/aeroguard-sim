"""
AeroGuard v6.0 — Aerospace Hazard Intelligence & Response Research Simulator

IMPORTANT:
- All telemetry, sensors, failure injection, predictions, physics, and actuators are simulated.
- This is an educational/research prototype, not certified aerospace/flight software.
- Do not connect it to real spacecraft, aircraft, life-support, fire-suppression, or power hardware.
- The material reference rows are inherited app sample data and are NOT verified NASA measurements.
"""
from __future__ import annotations

import json
import math
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

VERSION = "6.0"
DB_PATH = Path("aeroguard_v6.sqlite3")
MODULES = [
    "ISS - Destiny Laboratory",
    "ISS - Harmony Node 2",
    "Lunar Gateway - HALO",
    "Orion Crew Capsule",
]
MATERIALS = [
    "Gaseous Propane", "Solid PMMA (Acrylic)", "Methane Jet",
    "ETFE Wire Insulation", "Ethanol Droplet", "Cotton-Fiberglass Nomex",
    "Cast PMMA Rod", "n-Heptane Droplet", "Ethylene Coflow", "Silicone Composite",
]
SIGNALS = ["CO_ppm", "Smoke_pct", "Temp_C", "O2_pct", "CO2_ppm",
           "Pressure_kPa", "Humidity_pct"]

st.set_page_config(
    page_title=f"AeroGuard v{VERSION}",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown("""
<style>
.stApp {background: #09111e;}
section[data-testid="stSidebar"] {background: #111d2e;}
div[data-testid="stMetric"] {
  background: #132238; border: 1px solid #29405e;
  padding: 12px; border-radius: 12px;
}
.ag-banner {padding: 13px; border-radius: 10px; text-align:center;
  font-weight:700; margin: 8px 0 16px;}
.ag-ok {background:#073b32; color:#d1fae5; border:1px solid #10b981;}
.ag-warn {background:#49320a; color:#fef3c7; border:1px solid #f59e0b;}
.ag-alarm {background:#551b25; color:#fee2e2; border:1px solid #ef4444;}
.small-muted {color:#9fb1c8; font-size:0.88rem;}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def reference_data() -> pd.DataFrame:
    # Preserved from the supplied AeroGuard v5 application.
    # These are app-provided illustrative rows, not validated NASA test data.
    return pd.DataFrame({
        "Mission_ID": ["FLEX-01", "BASS-02", "SPICE-01", "SAME-R", "FLEX-02",
                       "Saffire-IV", "BASS-M", "FLEX-ICE", "ACME-E", "Saffire-V"],
        "Fuel_Material": MATERIALS,
        "Class": ["Hydrocarbon Gas", "Thermoplastic", "Hydrocarbon Gas",
                  "Avionics Wiring", "Liquid Propellant", "Crew Fabric",
                  "Thermoplastic", "Liquid Fuel", "Gas Jet", "Sealant/Polymer"],
        "Oxygen_Pct": [18, 30, 21, 24.5, 35, 26, 22, 28, 23.5, 32],
        "Airflow_cm_s": [5, 10.2, 2.1, .8, 15, 12, 1.5, 4, 6.5, 8],
        "Flame_Spread_mm_s": [3.2, 14.8, 4.5, 1.9, 22.4, 18.5, 2.8, 11.2, 7.6, 13.4],
        "Radiative_Flux_kW_m2": [12.5, 45, 18.2, 9.4, 58, 38.5, 14, 32.1, 21, 36.8],
        "Limiting_O2_Index": [15.5, 17.8, 16.2, 19, 14.8, 20.5, 18.2, 15.2, 16, 21],
        "Quench_Difficulty": ["Low", "High", "Moderate", "Moderate", "Critical",
                              "High", "Low", "High", "Moderate", "High"],
    })


REF = reference_data()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db_connect():
    con = sqlite3.connect(DB_PATH, timeout=15, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with db_connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY, timestamp TEXT, username TEXT, module TEXT,
            scenario TEXT, event_type TEXT, status TEXT, risk_score REAL,
            details TEXT
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, username TEXT,
            module TEXT, scenario TEXT, sensor_json TEXT, risk_score REAL,
            flags_json TEXT
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS scenarios (
            id TEXT PRIMARY KEY, timestamp TEXT, username TEXT, name TEXT,
            config_json TEXT, result_json TEXT
        )""")
        con.commit()


init_db()


def log_event(event_type: str, status: str, details: dict | None = None):
    s = st.session_state
    with db_connect() as con:
        con.execute(
            "INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), utc_now(), s.get("username", "guest"),
             s.get("module", MODULES[0]), s.get("scenario_name", "Manual scenario"),
             event_type, status, float(s.get("risk_score", 0.0)),
             json.dumps(details or {}, default=str)),
        )
        con.commit()


def base_sensor_sample(active: bool, severity: float, noise: float,
                       oxygen: float, seed: int | None = None) -> dict:
    """Synthetic signals; deliberately not a real sensor model."""
    rng = np.random.default_rng(seed)
    h = severity if active else 0.0
    return {
        "CO_ppm": float(np.clip(rng.normal(1.1 + 10.0*h, .30*noise), 0, 100)),
        "Smoke_pct": float(np.clip(rng.normal(.06 + .72*h, .035*noise), 0, 5)),
        "Temp_C": float(np.clip(rng.normal(22.0 + 28.0*h, .45*noise), -20, 180)),
        "O2_pct": float(np.clip(rng.normal(oxygen - 1.0*h, .18*noise), 0, 100)),
        "CO2_ppm": float(np.clip(rng.normal(500 + 900*h, 22*noise), 0, 12000)),
        "Pressure_kPa": float(np.clip(rng.normal(101.3 - 2.0*h, .10*noise), 40, 120)),
        "Humidity_pct": float(np.clip(rng.normal(42 + 4*h, 1.0*noise), 0, 100)),
    }


def apply_sensor_faults(readings: dict, faults: list[str]) -> tuple[dict, list[str]]:
    """Apply transparent test faults to synthetic sensor channels."""
    x = dict(readings)
    notes = []
    if "Smoke sensor disconnected" in faults:
        x["Smoke_pct"] = None
        notes.append("Smoke channel unavailable")
    if "CO sensor stuck" in faults:
        x["CO_ppm"] = 1.1
        notes.append("CO channel frozen at a constant value")
    if "Temperature sensor drift" in faults:
        x["Temp_C"] = float(x["Temp_C"] + 12.0)
        notes.append("Temperature channel has injected +12°C drift")
    if "Pressure sensor noisy" in faults:
        x["Pressure_kPa"] = float(np.clip(x["Pressure_kPa"] + 5.0, 40, 120))
        notes.append("Pressure channel has injected offset")
    return x, notes


def sensor_fusion(x: dict) -> tuple[float, list[str], dict]:
    """Weighted, explainable rule score. Not trained AI and not a certified fire model."""
    rules = {
        "CO elevated": (x.get("CO_ppm") is not None and x["CO_ppm"] >= 8, .22),
        "Smoke elevated": (x.get("Smoke_pct") is not None and x["Smoke_pct"] >= .35, .27),
        "Temperature elevated": (x.get("Temp_C") is not None and x["Temp_C"] >= 34, .22),
        "CO2 elevated": (x.get("CO2_ppm") is not None and x["CO2_ppm"] >= 1100, .12),
        "Oxygen deviation": (x.get("O2_pct") is not None and x["O2_pct"] <= 19, .08),
        "Pressure deviation": (x.get("Pressure_kPa") is not None and x["Pressure_kPa"] <= 98, .09),
    }
    weights = {name: weight for name, (triggered, weight) in rules.items() if triggered}
    flags = list(weights)
    available = sum(v is not None for v in x.values())
    health = available / max(1, len(x))
    score = min(1.0, sum(weights.values()))
    # Missing sensor data is reported separately and cannot be interpreted as safe.
    if health < 1:
        flags.append(f"Sensor coverage degraded ({health:.0%} channels available)")
    return score, flags, {"contributions": weights, "coverage": health}


def risk_label(score: float) -> str:
    if score >= .65:
        return "HIGH"
    if score >= .30:
        return "ELEVATED"
    return "LOW"


def illustrative_physics(material: str, oxygen: float, airflow: float,
                         hvac_isolated: bool, rack_power_cut: bool) -> dict:
    """Simple inherited illustrative equation; not validated combustion physics."""
    row = REF.loc[REF["Fuel_Material"] == material].iloc[0]
    effective_flow = .2 if hvac_isolated else airflow
    flow_factor = 1.4 if effective_flow < 2 else 1.0 + effective_flow / 14.0
    oxygen_factor = (max(1.0, oxygen) / 21.0) ** 1.85
    power_factor = .35 if rack_power_cut else 1.0
    spread = float(row["Flame_Spread_mm_s"] * oxygen_factor * flow_factor * power_factor)
    return {
        "spread_mm_s": max(0.0, spread),
        "flux_kw_m2": float(row["Radiative_Flux_kW_m2"] * oxygen_factor),
        "oxygen_index_margin": float(oxygen - row["Limiting_O2_Index"]),
    }


def strategy_estimate(name: str, x: dict, material: str, oxygen: float,
                      airflow: float, duration_s: int) -> dict:
    """Compare configurable virtual strategies using toy-model assumptions only."""
    settings = {
        "Monitor only": (False, False, 1.00),
        "Ventilation isolation": (True, False, .82),
        "Rack power reduction": (False, True, .72),
        "Combined virtual response": (True, True, .55),
    }
    hvac, power, response_factor = settings[name]
    p = illustrative_physics(material, oxygen, airflow, hvac, power)
    severity = min(1.0, max(.05, (x.get("Smoke_pct") or .05) / .8))
    projected_damage = min(100.0, p["spread_mm_s"] * duration_s * .02 * response_factor)
    projected_risk = min(1.0, (p["spread_mm_s"] / 35.0) * .55 +
                         severity * .35 + (0.10 if not hvac else 0.0))
    return {
        "Strategy": name,
        "Virtual HVAC isolation": hvac,
        "Virtual rack power reduction": power,
        "Illustrative risk score": round(projected_risk, 3),
        "Illustrative damage index (%)": round(projected_damage, 2),
        "Model note": "Toy-model comparison; not an operational recommendation",
    }


def forecast_frame(history: pd.DataFrame, horizon_seconds: int) -> pd.DataFrame:
    rows = []
    if len(history) < 5:
        return pd.DataFrame()
    recent = history.tail(30).reset_index(drop=True)
    for col in ["CO_ppm", "Smoke_pct", "Temp_C"]:
        vals = pd.to_numeric(recent[col], errors="coerce").dropna()
        if len(vals) < 5:
            continue
        xx = np.arange(len(vals))
        slope, intercept = np.polyfit(xx, vals.to_numpy(), 1)
        projected = max(0.0, float(intercept + slope * (len(vals)-1 + horizon_seconds)))
        residual = vals.to_numpy() - (slope*xx + intercept)
        uncertainty = float(np.std(residual)) if len(residual) > 1 else 0.0
        rows.append({
            "Signal": col, "Latest": float(vals.iloc[-1]),
            "Trend per sample": float(slope),
            f"Illustrative projection (+{horizon_seconds} samples)": projected,
            "Residual spread (not calibrated confidence)": uncertainty,
        })
    return pd.DataFrame(rows)


def persist_telemetry(x: dict, score: float, flags: list[str]):
    s = st.session_state
    with db_connect() as con:
        con.execute(
            """INSERT INTO telemetry(timestamp,username,module,scenario,sensor_json,risk_score,flags_json)
               VALUES(?,?,?,?,?,?,?)""",
            (utc_now(), s.username, s.module, s.scenario_name,
             json.dumps(x), score, json.dumps(flags)),
        )
        con.commit()


def load_user_table(table: str, user: str, limit: int = 2000) -> pd.DataFrame:
    allowed = {"events", "telemetry", "scenarios"}
    if table not in allowed:
        raise ValueError("Unknown table")
    with db_connect() as con:
        return pd.read_sql_query(
            f"SELECT * FROM {table} WHERE username=? ORDER BY timestamp DESC LIMIT ?",
            con, params=(user, limit),
        )


def save_scenario(name: str, config: dict, result: dict):
    s = st.session_state
    with db_connect() as con:
        con.execute(
            "INSERT INTO scenarios VALUES(?,?,?,?,?,?)",
            (str(uuid.uuid4()), utc_now(), s.username, name,
             json.dumps(config, default=str), json.dumps(result, default=str)),
        )
        con.commit()
    log_event("SCENARIO_SAVED", "SAVED", {"name": name})


# ---------- Session state ----------
defaults = {
    "logged_in": False, "username": "", "module": MODULES[0],
    "material": MATERIALS[0], "oxygen": 24.5, "airflow": 6.5,
    "scenario_name": "Baseline habitat", "severity": .0,
    "hazard_active": False, "hvac_isolated": False, "rack_power_cut": False,
    "drill_started": None, "drill_last_tick": None, "damage_index": 0.0,
    "faults": [], "noise": 1.0, "history": [], "last_sample": 0.0,
    "sensor": {}, "risk_score": 0.0, "flags": [], "live_stream": False,
    "last_action": "System initialized", "duration": 30,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value
s = st.session_state

# Demo access only — intentionally no fake OAuth claims.
if not s.logged_in:
    _, center, _ = st.columns([1, 1.25, 1])
    with center:
        st.title("🛰️ AeroGuard Gateway")
        st.subheader("Intelligent aerospace hazard research simulator")
        st.warning("Demo access only. No Google/X authentication or identity verification is performed.")
        if st.button("Enter AeroGuard Demo", type="primary", use_container_width=True):
            s.logged_in = True
            s.username = "demo_operator"
            log_event("SESSION_START", "DEMO", {"authentication": "demo-only"})
            st.rerun()
    st.stop()

# ---------- Sidebar controls ----------
st.sidebar.title("🛰️ AeroGuard Control Room")
st.sidebar.caption(f"Demo operator: {s.username}")
if st.sidebar.button("Log out / switch demo session"):
    s.logged_in = False
    s.username = ""
    st.rerun()

s.module = st.sidebar.selectbox("Habitat module", MODULES, index=MODULES.index(s.module))
s.material = st.sidebar.selectbox("Reference material", MATERIALS, index=MATERIALS.index(s.material))
s.oxygen = st.sidebar.slider("Ambient oxygen (%)", 10.0, 50.0, float(s.oxygen), .5)
s.airflow = st.sidebar.slider("Ventilation velocity (cm/s)", 0.0, 50.0, float(s.airflow), .5)
s.duration = st.sidebar.select_slider("Scenario duration (seconds)", [10, 20, 30, 45, 60, 90], value=s.duration)
s.noise = st.sidebar.slider("Synthetic sensor noise", .2, 3.0, float(s.noise), .1)
s.live_stream = st.sidebar.toggle("Auto-refresh synthetic telemetry", value=s.live_stream)
st.sidebar.caption("Every control affects simulator state only; no physical hardware is connected.")

cstart, creset = st.sidebar.columns(2)
if cstart.button("Start timed fire drill", type="primary", use_container_width=True):
    s.hazard_active = True
    s.severity = .75
    s.drill_started = time.monotonic()
    s.drill_last_tick = s.drill_started
    s.scenario_name = "Timed fire-drill simulation"
    s.last_action = "Timed synthetic fire drill started"
    log_event("DRILL_START", "ACTIVE", {"severity": s.severity, "duration_seconds": s.duration})
if creset.button("Reset", use_container_width=True):
    s.hazard_active = False
    s.severity = 0.0
    s.drill_started = None
    s.drill_last_tick = None
    s.damage_index = 0.0
    s.hvac_isolated = False
    s.rack_power_cut = False
    s.faults = []
    s.scenario_name = "Baseline habitat"
    s.last_action = "Simulator reset"
    log_event("SIMULATOR_RESET", "RESET")
    st.rerun()

# Scenario selection to reproduce known cases
scenario_presets = {
    "Baseline habitat": (False, 0.0),
    "Slow thermal rise": (True, .35),
    "Rapid smoke event": (True, .85),
    "High-temperature equipment fault": (True, .70),
}
preset = st.sidebar.selectbox("Scenario preset", list(scenario_presets), index=0)
if st.sidebar.button("Load selected scenario"):
    active, sev = scenario_presets[preset]
    s.hazard_active, s.severity = active, sev
    s.drill_started = time.monotonic() if active else None
    s.drill_last_tick = s.drill_started
    s.scenario_name = preset
    s.last_action = f"Loaded scenario: {preset}"
    s.hvac_isolated = False
    s.rack_power_cut = False
    log_event("PRESET_LOADED", "LOADED", {"preset": preset, "severity": sev})
    st.rerun()

# Generate one sample on each normal rerun, or once per second in live mode.
now = time.monotonic()
if not s.sensor or now - s.last_sample >= 1.0:
    raw = base_sensor_sample(s.hazard_active, s.severity, s.noise, s.oxygen)
    x, fault_notes = apply_sensor_faults(raw, s.faults)
    score, flags, fusion = sensor_fusion(x)
    if fault_notes:
        flags.extend(fault_notes)
    s.sensor, s.risk_score, s.flags = x, score, flags
    s.last_sample = now
    row = {"timestamp": utc_now(), **x, "risk_score": score, "scenario": s.scenario_name}
    s.history.append(row)
    s.history = s.history[-600:]
    persist_telemetry(x, score, flags)
else:
    x = s.sensor
    score, flags, fusion = sensor_fusion(x)
    flags = list(s.flags)

# Time-based drill progression. Damage is illustrative and advances with elapsed time,
# not with the number of Streamlit reruns.
drill_remaining = 0
if s.hazard_active and s.drill_started is not None:
    elapsed = max(0.0, time.monotonic() - s.drill_started)
    drill_remaining = max(0, math.ceil(s.duration - elapsed))
    tick_now = time.monotonic()
    dt = max(0.0, min(2.0, tick_now - (s.drill_last_tick or tick_now)))
    toy = illustrative_physics(s.material, s.oxygen, s.airflow,
                               s.hvac_isolated, s.rack_power_cut)
    s.damage_index = min(100.0, s.damage_index + toy["spread_mm_s"] * dt * .02)
    s.drill_last_tick = tick_now
    if elapsed >= s.duration:
        s.hazard_active = False
        s.drill_started = None
        log_event("DRILL_COMPLETE", "COMPLETED", {"damage_index": round(s.damage_index, 2)})

# Header / KPIs
st.title("🛰️ AeroGuard v6.0")
st.caption("Hazard intelligence · Digital habitat twin · Resilience laboratory · Scenario benchmarking")
banner = ("ag-alarm" if score >= .65 else "ag-warn" if score >= .30 else "ag-ok")
banner_text = ("HIGH SIMULATED RISK — investigate the test scenario" if score >= .65 else
               "ELEVATED SIMULATED RISK — review contributing channels" if score >= .30 else
               "SIMULATOR NOMINAL — no configured high-risk rule triggered")
st.markdown(f'<div class="ag-banner {banner}">{banner_text}</div>', unsafe_allow_html=True)

k = st.columns(6)
k[0].metric("Risk score", f"{score:.0%}", risk_label(score))
k[1].metric("CO", "Unavailable" if x["CO_ppm"] is None else f"{x['CO_ppm']:.1f} ppm")
k[2].metric("Smoke", "Unavailable" if x["Smoke_pct"] is None else f"{x['Smoke_pct']:.3f}%")
k[3].metric("Temperature", f"{x['Temp_C']:.1f} °C")
k[4].metric("Sensor coverage", f"{fusion['coverage']:.0%}")
k[5].metric("Drill / damage", f"{drill_remaining}s left" if s.hazard_active else f"{s.damage_index:.2f}% damage")
st.warning(
    "Research prototype only: synthetic signals, illustrative equations and virtual controls. "
    "No output is a fire-safety instruction, validated prediction, or spacecraft operating limit."
)

tabs = st.tabs([
    "Overview & Digital Twin", "Sensor Intelligence", "Prediction",
    "Response Comparison", "Fault & Resilience Lab", "Scenario Replay",
    "Benchmark Center", "Audit & Data",
])

# ---------- 1. Overview / digital twin ----------
with tabs[0]:
    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("Habitat zone map")
        st.caption("Conceptual zone layout. The highlighted zone is a scenario label, not a physical location estimate.")
        zones = pd.DataFrame({
            "zone": ["Crew quarters", "Avionics rack", "Airlock", "Lab workbench", "Utility bay"],
            "x": [1, 3, 5, 1, 3], "y": [2, 2, 2, 0, 0],
            "risk": [score*.25, score, score*.15, score*.45, score*.30],
        })
        fig = px.scatter(
            zones, x="x", y="y", color="risk", size="risk",
            text="zone", color_continuous_scale="Turbo",
            range_color=(0, 1), title="Illustrative habitat risk zoning",
        )
        fig.update_traces(textposition="top center", marker=dict(sizemin=14))
        fig.update_layout(template="plotly_dark", height=360,
                          xaxis=dict(visible=False), yaxis=dict(visible=False))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("The current prototype uses a conceptual zone map, not CAD geometry or validated smoke-flow simulation.")
    with right:
        st.subheader("Current habitat state")
        st.metric("Virtual HVAC", "ISOLATED" if s.hvac_isolated else "ACTIVE")
        st.metric("Virtual rack power", "REDUCED" if s.rack_power_cut else "NORMAL")
        st.metric("Injected sensor faults", len(s.faults))
        st.write("**Selected module:**", s.module)
        st.write("**Material reference:**", s.material)
        st.write("**Last simulator action:**", s.last_action)
        p = illustrative_physics(s.material, s.oxygen, s.airflow,
                                 s.hvac_isolated, s.rack_power_cut)
        st.write(f"Toy-model spread index: **{p['spread_mm_s']:.2f}**")
        st.write(f"Toy-model radiative index: **{p['flux_kw_m2']:.2f}**")
    st.subheader("3D habitat concept")
    fig3 = go.Figure()
    # Simple cuboid outline + equipment and crew markers.
    corners = [(0,0,0),(10,0,0),(10,5,0),(0,5,0),(0,0,3),(10,0,3),(10,5,3),(0,5,3)]
    edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
    for a, b in edges:
        fig3.add_trace(go.Scatter3d(
            x=[corners[a][0], corners[b][0]], y=[corners[a][1], corners[b][1]],
            z=[corners[a][2], corners[b][2]], mode="lines",
            line=dict(color="#7c93b3", width=5), showlegend=False,
        ))
    fig3.add_trace(go.Scatter3d(
        x=[7.5, 2.0, 5.0], y=[2.5, 2.5, 1.0], z=[1.2, 1.0, 2.0],
        mode="markers+text", text=["Avionics rack", "Crew zone", "Airlock"],
        textposition="top center", marker=dict(size=[12, 8, 7], color=["red", "cyan", "orange"]),
        name="Habitat systems",
    ))
    fig3.update_layout(template="plotly_dark", height=430,
                       scene=dict(aspectmode="data", xaxis_title="X", yaxis_title="Y", zaxis_title="Z"))
    st.plotly_chart(fig3, use_container_width=True)

# ---------- 2. Sensor fusion ----------
with tabs[1]:
    st.subheader("Multi-sensor intelligence")
    st.write("A weighted, explainable rule engine combines available channels. It is not a trained AI model.")
    contributions = fusion["contributions"]
    if contributions:
        st.dataframe(pd.DataFrame(
            [{"Triggered rule": name, "Score contribution": weight} for name, weight in contributions.items()]
        ), use_container_width=True, hide_index=True)
    else:
        st.success("No configured hazard threshold is currently triggered.")
    if flags:
        for flag in flags:
            st.warning(flag)
    hist = pd.DataFrame(s.history)
    if not hist.empty:
        available_signals = [c for c in SIGNALS if c in hist.columns and hist[c].notna().any()]
        selected = st.multiselect("Telemetry channels", available_signals,
                                  default=[c for c in ["CO_ppm", "Smoke_pct", "Temp_C"] if c in available_signals])
        if selected:
            st.line_chart(hist.set_index("timestamp")[selected], height=320)
        st.dataframe(hist.tail(30), use_container_width=True, hide_index=True)
    st.subheader("Sensor health diagnostics")
    health_rows = []
    for signal in SIGNALS:
        value = x.get(signal)
        health_rows.append({
            "Channel": signal,
            "Current value": "MISSING" if value is None else value,
            "Status": "UNAVAILABLE" if value is None else "SIMULATED / AVAILABLE",
        })
    st.dataframe(pd.DataFrame(health_rows), use_container_width=True, hide_index=True)

# ---------- 3. Prediction ----------
with tabs[2]:
    st.subheader("Short-horizon trend projection")
    horizon = st.slider("Projection horizon (future samples)", 1, 30, 8)
    forecast = forecast_frame(pd.DataFrame(s.history), horizon)
    if forecast.empty:
        st.info("At least five usable samples per channel are needed. Enable auto-refresh or interact with the simulator to collect samples.")
    else:
        st.dataframe(forecast, use_container_width=True, hide_index=True)
        st.caption("Linear extrapolation only. Residual spread is descriptive uncertainty, not a calibrated probability or confidence interval.")
    st.subheader("What the prediction does — and does not — mean")
    st.markdown("""
    - Fits a straight line to recent synthetic readings.
    - Extrapolates the line over a user-selected number of samples.
    - Reports residual spread to show how scattered recent points are around the fitted line.
    - Does **not** predict real fire development, crew exposure, or safe response time.
    """)

# ---------- 4. Response comparison ----------
with tabs[3]:
    st.subheader("Virtual response strategy comparison")
    st.info("This is a decision-support experiment using illustrative equations. It does not select or execute real emergency actions.")
    compare_duration = st.slider("Comparison duration (seconds)", 10, 180, 45)
    strategy_names = ["Monitor only", "Ventilation isolation", "Rack power reduction", "Combined virtual response"]
    results = pd.DataFrame([
        strategy_estimate(name, x, s.material, s.oxygen, s.airflow, compare_duration)
        for name in strategy_names
    ])
    st.dataframe(results, use_container_width=True, hide_index=True)
    chart = px.bar(results, x="Strategy", y="Illustrative damage index (%)",
                   color="Strategy", title="Toy-model strategy comparison")
    chart.update_layout(template="plotly_dark", showlegend=False)
    st.plotly_chart(chart, use_container_width=True)
    st.subheader("Virtual interlocks (simulator only)")
    vc1, vc2, vc3 = st.columns(3)
    with vc1:
        if st.button("Toggle virtual HVAC isolation"):
            s.hvac_isolated = not s.hvac_isolated
            s.last_action = "Virtual HVAC " + ("isolated" if s.hvac_isolated else "restored")
            log_event("HVAC_OVERRIDE", "ISOLATED" if s.hvac_isolated else "RESTORED")
            st.rerun()
        st.metric("HVAC state", "ISOLATED" if s.hvac_isolated else "ACTIVE")
    with vc2:
        if st.button("Toggle virtual rack power reduction"):
            s.rack_power_cut = not s.rack_power_cut
            s.last_action = "Virtual rack power " + ("reduced" if s.rack_power_cut else "restored")
            log_event("RACK_POWER_OVERRIDE", "REDUCED" if s.rack_power_cut else "RESTORED")
            st.rerun()
        st.metric("Rack power", "REDUCED" if s.rack_power_cut else "NORMAL")
    with vc3:
        if st.button("Trigger virtual water-mist event", disabled=not s.hazard_active):
            s.hazard_active = False
            s.drill_started = None
            s.last_action = "Virtual water-mist event recorded"
            log_event("VIRTUAL_SUPPRESSION", "SIMULATED_EVENT", {"damage_index_retained": s.damage_index})
            st.rerun()
        st.metric("Virtual suppressor", "READY")

    chosen = st.selectbox("Record a virtual operator decision", strategy_names)
    reason = st.text_area("Decision rationale / experiment notes", placeholder="Explain why this strategy is being tested...")
    if st.button("Record decision in audit trail"):
        log_event("VIRTUAL_STRATEGY_SELECTED", "RECORDED",
                  {"strategy": chosen, "rationale": reason, "comparison": results.to_dict("records")})
        s.last_action = f"Recorded strategy experiment: {chosen}"
        st.success("Experiment decision recorded in the local audit database.")

# ---------- 5. Fault injection ----------
with tabs[4]:
    st.subheader("Failure-injection and resilience laboratory")
    st.write("Intentionally degrade synthetic channels to test whether the interface reports unreliable input.")
    fault_options = [
        "Smoke sensor disconnected", "CO sensor stuck",
        "Temperature sensor drift", "Pressure sensor noisy",
    ]
    new_faults = st.multiselect("Inject simulated sensor faults", fault_options, default=s.faults)
    if st.button("Apply fault configuration"):
        s.faults = new_faults
        log_event("SENSOR_FAULT_CONFIGURATION", "UPDATED", {"faults": new_faults})
        s.last_sample = 0
        st.rerun()
    if s.faults:
        st.error("Fault injection active: do not interpret missing or degraded channels as evidence of safety.")
        for item in s.faults:
            st.write("•", item)
    else:
        st.success("No injected sensor faults.")
    st.subheader("Resilience test checklist")
    st.markdown("""
    1. Record a baseline with no injected faults.
    2. Disconnect the smoke channel and verify the coverage warning.
    3. Freeze the CO channel and observe whether other channels still contribute.
    4. Add temperature drift and note the change in the rule score.
    5. Clear all faults and compare the baseline again.
    """)
    if st.button("Log current resilience test result"):
        log_event("RESILIENCE_TEST", "OBSERVATION_RECORDED",
                  {"faults": s.faults, "coverage": fusion["coverage"],
                   "risk_score": score, "flags": flags})
        st.success("Resilience observation saved.")

# ---------- 6. Scenario replay / save ----------
with tabs[5]:
    st.subheader("Scenario laboratory")
    st.write("Save a reproducible snapshot of the current synthetic test configuration and outputs.")
    scenario_label = st.text_input("Scenario name", value=s.scenario_name)
    if st.button("Save current scenario snapshot", type="primary"):
        config = {
            "module": s.module, "material": s.material, "oxygen": s.oxygen,
            "airflow": s.airflow, "scenario": s.scenario_name,
            "hazard_active": s.hazard_active, "severity": s.severity,
            "faults": s.faults, "hvac_isolated": s.hvac_isolated,
            "rack_power_cut": s.rack_power_cut,
        }
        result = {"sensor": x, "risk_score": score, "flags": flags}
        save_scenario(scenario_label, config, result)
        st.success("Scenario snapshot saved to the local SQLite database.")
    saved = load_user_table("scenarios", s.username)
    if saved.empty:
        st.info("No saved scenarios yet.")
    else:
        st.dataframe(saved[["timestamp", "name", "config_json", "result_json"]],
                     use_container_width=True, hide_index=True)
        selected_id = st.selectbox("Select saved scenario ID", saved["id"].tolist())
        if st.button("Load selected scenario configuration"):
            row = saved.loc[saved["id"] == selected_id].iloc[0]
            cfg = json.loads(row["config_json"])
            s.module = cfg.get("module", s.module)
            s.material = cfg.get("material", s.material)
            s.oxygen = cfg.get("oxygen", s.oxygen)
            s.airflow = cfg.get("airflow", s.airflow)
            s.scenario_name = cfg.get("scenario", row["name"])
            s.hazard_active = cfg.get("hazard_active", False)
            s.severity = cfg.get("severity", 0.0)
            s.faults = cfg.get("faults", [])
            s.hvac_isolated = cfg.get("hvac_isolated", False)
            s.rack_power_cut = cfg.get("rack_power_cut", False)
            s.last_sample = 0
            log_event("SCENARIO_REPLAYED", "LOADED", {"scenario_id": selected_id})
            st.rerun()

# ---------- 7. Benchmark center ----------
with tabs[6]:
    st.subheader("Repeatable benchmark center")
    st.write("Run a fixed suite of synthetic test cases and compare the rule-based detector with a simple single-channel baseline.")
    benchmark_cases = [
        ("Normal baseline", False, 0.0),
        ("Slow thermal rise", True, .30),
        ("Moderate mixed signature", True, .55),
        ("Rapid mixed signature", True, .90),
        ("Low-severity event", True, .20),
    ]
    if st.button("Run benchmark suite", type="primary"):
        rows = []
        for case_name, active, sev in benchmark_cases:
            sample = base_sensor_sample(active, sev, 0.0, s.oxygen, seed=100 + len(rows))
            fused, fused_flags, _ = sensor_fusion(sample)
            baseline = 1 if sample["Smoke_pct"] >= .35 else 0
            fused_detect = 1 if fused >= .30 else 0
            expected = 1 if active and sev >= .50 else 0
            rows.append({
                "Scenario": case_name, "Expected positive (test label)": expected,
                "Fusion detector positive": fused_detect,
                "Smoke-only baseline positive": baseline,
                "Fusion score": round(fused, 3),
                "Fusion flags": "; ".join(fused_flags) or "None",
            })
        bench = pd.DataFrame(rows)
        st.session_state["last_benchmark"] = bench
        log_event("BENCHMARK_RUN", "COMPLETED", {"rows": rows})
    bench = st.session_state.get("last_benchmark")
    if bench is not None:
        st.dataframe(bench, use_container_width=True, hide_index=True)
        st.caption("Small synthetic demonstration suite only. Labels and results are not a validated dataset or proof of field performance.")
        st.download_button("Download benchmark CSV", bench.to_csv(index=False).encode(),
                           "aeroguard_v6_benchmark.csv", "text/csv")
        # Accuracy-like metrics are explicitly limited to this tiny artificial suite.
        y = bench["Expected positive (test label)"].to_numpy()
        pred = bench["Fusion detector positive"].to_numpy()
        tp = int(((y == 1) & (pred == 1)).sum())
        tn = int(((y == 0) & (pred == 0)).sum())
        fp = int(((y == 0) & (pred == 1)).sum())
        fn = int(((y == 1) & (pred == 0)).sum())
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("TP", tp); m2.metric("TN", tn); m3.metric("FP", fp); m4.metric("FN", fn)
        st.caption("These counts describe only the generated demo cases. Do not present them as real-world detector accuracy.")

# ---------- 8. Audit / data ----------
with tabs[7]:
    st.subheader("Persistent audit trail")
    events = load_user_table("events", s.username)
    telemetry = load_user_table("telemetry", s.username)
    scenarios = load_user_table("scenarios", s.username)
    a, b, c = st.columns(3)
    a.metric("Audit events", len(events))
    b.metric("Telemetry rows", len(telemetry))
    c.metric("Saved scenarios", len(scenarios))
    if not events.empty:
        st.dataframe(events, use_container_width=True, hide_index=True)
        st.download_button("Export events CSV", events.to_csv(index=False).encode(),
                           "aeroguard_v6_events.csv", "text/csv")
        st.download_button("Export events JSON", events.to_json(orient="records", indent=2).encode(),
                           "aeroguard_v6_events.json", "application/json")
    if not telemetry.empty:
        st.download_button("Export telemetry CSV", telemetry.to_csv(index=False).encode(),
                           "aeroguard_v6_telemetry.csv", "text/csv")
    st.write(f"**Local database:** `{DB_PATH.resolve()}`")
    st.write(f"**Last action:** {s.last_action}")
    st.subheader("Preserved app reference dataset")
    st.caption("Inherited sample values; not independently verified NASA measurements or certified operating limits.")
    st.dataframe(REF, use_container_width=True, hide_index=True)
    st.download_button("Export reference table CSV", REF.to_csv(index=False).encode(),
                       "aeroguard_reference_sample_data.csv", "text/csv")
    if st.button("Delete my local demo records", type="secondary"):
        st.session_state["confirm_delete_records"] = True
    if st.session_state.get("confirm_delete_records", False):
        st.error("This permanently deletes this demo username's local event, telemetry and scenario rows.")
        yes, no = st.columns(2)
        if yes.button("Confirm permanent deletion", type="primary"):
            with db_connect() as con:
                for table in ("events", "telemetry", "scenarios"):
                    con.execute(f"DELETE FROM {table} WHERE username=?", (s.username,))
                con.commit()
            st.session_state["confirm_delete_records"] = False
            st.success("Local demo records deleted.")
            st.rerun()
        if no.button("Cancel deletion"):
            st.session_state["confirm_delete_records"] = False
            st.rerun()

st.divider()
st.caption(
    "AeroGuard v6.0 is a local educational prototype. Authentication is demo-only; "
    "telemetry is synthetic; prediction and response calculations are illustrative; "
    "the SQLite database is local to the machine running Streamlit."
)

if s.live_stream:
    time.sleep(1)
    st.rerun()
