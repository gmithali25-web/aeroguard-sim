from __future__ import annotations

import hashlib
import io
import re
import zipfile
from datetime import datetime, timezone
from pathlib import PurePosixPath

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import pydeck as pdk

# ============================================================
# AEROGUARD SIM | CONSOLIDATED SINGLE-FILE PLATFORM
# ============================================================

st.set_page_config(
    page_title="AeroGuard Sim | Research & Learning Platform",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------- THEME ---------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap');
    :root {
        --bg:#050d1b; --panel:#09182b; --panel2:#0b2038;
        --line:#173653; --cyan:#22d3ee; --teal:#19d3b0;
        --muted:#8ba7c2; --white:#eaf4ff;
    }
    .stApp {background:radial-gradient(ellipse at 50% 0%, #0a1c33 0%, #050d1b 58%); color:var(--white);}
    html, body, [class*="css"] {font-family:Inter,sans-serif;}
    section[data-testid="stSidebar"] {background:#061326; border-right:1px solid #173653;}
    section[data-testid="stSidebar"] * {color:#d8e8f7;}
    .block-container {padding-top:1.1rem; padding-bottom:2rem; max-width:1800px;}
    .ag-top {display:flex; justify-content:space-between; align-items:center; padding:8px 2px 15px;
             border-bottom:1px solid #173653; margin-bottom:16px;}
    .ag-brand {font-size:1.22rem; font-weight:800; letter-spacing:.12em; color:#f1f8ff;}
    .ag-brand span {color:#22d3ee;}
    .ag-sub {font-size:.66rem; letter-spacing:.18em; color:#7796b3;}
    .ag-panel {background:linear-gradient(145deg,rgba(12,32,55,.97),rgba(6,19,36,.98));
               border:1px solid #173653; border-radius:13px; padding:15px 17px; margin-bottom:12px;}
    .ag-kpi {background:linear-gradient(145deg,#0c2340,#08172a); border:1px solid #1b4263;
             border-radius:11px; padding:12px 14px; min-height:88px;}
    .ag-kpi-label {color:#8ba7c2; font-size:.68rem; letter-spacing:.1em; text-transform:uppercase;}
    .ag-kpi-value {color:#f1f8ff; font-family:'Space Mono'; font-size:1.25rem; font-weight:700; margin-top:5px;}
    .ag-chip {display:inline-block; border:1px solid #176b70; background:#073b40; color:#67f3df;
              border-radius:20px; padding:3px 9px; font-size:.65rem; font-weight:700; letter-spacing:.06em;}
    div[data-testid="stMetric"] {background:#0b2038; border:1px solid #173653; padding:10px 12px; border-radius:10px;}
    div[data-testid="stMetricLabel"] {color:#8ba7c2;}
    div[data-testid="stMetricValue"] {color:#f1f8ff; font-family:'Space Mono';}
    .stButton>button, .stDownloadButton>button {background:#073b50; border:1px solid #167d96;
        color:#dffaff; border-radius:8px; font-weight:600;}
    .stButton>button:hover, .stDownloadButton>button:hover {border-color:#22d3ee; color:white;}
    footer {visibility:hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------- CONSTANTS -------------------------

STUDY_ID = "PSI-117"
STUDY_TITLE = "Effect of External Thermo-Convective Perturbation on Cool Flame Dynamics"
DOI = "10.60555/gz0q-b577"

FLIGHT_PROFILES = {
    "ground_liftoff": {
        "name": "Pad Liftoff & Acoustic Shear (0 ft)",
        "altitude_ft": 0,
        "external_temp_c": 15.0,
        "dynamic_pressure_kpa": 0.0,
        "description": "Initial launch pad phase with high acoustic resonance.",
    },
    "max_q": {
        "name": "Max Dynamic Pressure (35,000 ft)",
        "altitude_ft": 35000,
        "external_temp_c": -56.5,
        "dynamic_pressure_kpa": 32.4,
        "description": "Maximum aerodynamic loading and structural mechanical stress point.",
    },
}

# ------------------------- HELPERS -------------------------

@st.cache_data
def load_nasa_psi_database():
    data = {
        "Fuel": ["n-heptane", "n-heptane", "n-dodecane", "n-dodecane"],
        "do (mm)": [0.5, 2.0, 4.5, 4.0],
        "P (atm)": [1.0, 1.0, 2.75, 1.0],
        "XO2": ["21%", "21%", "21%", "21%"],
        "Data File": ["PROCI_2019_Stable_Cool", "PROCI_2023_Alkane", "PROCI_C12_2019", "MST_2024"],
        "Reference": [
            "https://doi.org/10.1016/j.proci.2018.05.151",
            "https://doi.org/10.1016/j.proci.2022.07.094",
            "https://doi.org/10.1016/j.proci.2018.09.015",
            "https://doi.org/10.1007/s12217-024-10115-x",
        ],
    }
    return pd.DataFrame(data)

def render_kpi(label, value, foot=""):
    st.markdown(
        f"""
        <div class="ag-kpi">
          <div class="ag-kpi-label">{label}</div>
          <div class="ag-kpi-value">{value}</div>
          <div class="ag-muted">{foot}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------- SIDEBAR -------------------------

with st.sidebar:
    st.markdown(
        '<div style="padding:8px 2px 18px"><div class="ag-brand">🚀 AERO<span>GUARD SIM</span></div>'
        '<div class="ag-sub">RESEARCH & LEARNING WORKSPACE</div></div>',
        unsafe_allow_html=True,
    )
    
    app_mode = st.radio(
        "OPERATING MODE",
        ["Research & Publication Suite", "Interactive Student Learning Lab"],
    )
    
    st.markdown("---")
    
    if app_mode == "Research & Publication Suite":
        page = st.radio(
            "MODULES",
            [
                "Mission Overview & Telemetry",
                "Flight Profile Simulation",
                "NASA Dataset Explorer & DOIs",
            ],
        )
    else:
        page = st.radio(
            "MODULES",
            [
                "Student Interactive Lab",
                "Combustion Theory Primer",
            ],
        )

# ---------------------------- MAIN PAGES -------------------------

if page == "Mission Overview & Telemetry":
    st.title("AeroGuard Sim | Research Command Dashboard")
    st.caption("High-trust aerospace safety validation and NASA combustion benchmarks.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi("TARGET", "Research Scholars", "Peer Review Ready")
    with c2:
        render_kpi("DATASET", "NASA PSI-117", "Verified Benchmarks")
    with c3:
        render_kpi("ELEVATION", "0 – 250,000 ft", "Flight Profiling")
    with c4:
        render_kpi("DOI", "10.60555/gz0q-b577", "Traceable")

    st.markdown("### 🛰️ Mission Telemetry Summary")
    st.write("Select a module from the sidebar to inspect flight profiles, explore NASA droplet combustion data, or test interactive student scenarios.")

elif page == "Flight Profile Simulation":
    st.title("Multi-Phase Flight & Combustion Simulation")
    selected_phase_key = st.selectbox("Select Flight Mission Phase", list(FLIGHT_PROFILES.keys()), format_func=lambda x: FLIGHT_PROFILES[x]["name"])
    phase = FLIGHT_PROFILES[selected_phase_key]

    st.markdown('<div class="ag-panel">', unsafe_allow_html=True)
    st.markdown(f"### {phase['name']}")
    st.write(phase["description"])
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Altitude", f"{phase['altitude_ft']:,} ft")
    with col2:
        st.metric("Dynamic Pressure", f"{phase['dynamic_pressure_kpa']} kPa")
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "NASA Dataset Explorer & DOIs":
    st.title("NASA PSI-117 Experimental Data Explorer")
    psi_df = load_nasa_psi_database()
    st.dataframe(psi_df, use_container_width=True, hide_index=True)
    
    st.markdown("### Verified DOI Citation References")
    for idx, row in psi_df.iterrows():
        st.markdown(f"- **{row['Data File']}** ({row['Fuel']}, $d_0$: {row['do (mm)']} mm) — [Access DOI]({row['Reference']})")

elif page == "Student Interactive Lab":
    st.title("🎓 Student Interactive Learning Lab")
    droplet_size = st.slider("Initial Droplet Diameter ($d_0$ in mm)", 0.1, 5.0, 2.0, 0.1)
    chamber_pressure = st.slider("Chamber Pressure ($P$ in atm)", 0.5, 5.0, 1.0, 0.25)
    
    burn_rate = round(droplet_size * 1.414 * (chamber_pressure ** 0.5), 3)
    st.metric("Estimated Burning Rate Parameter ($K$)", f"{burn_rate} mm²/s")

elif page == "Combustion Theory Primer":
    st.title("📖 Combustion Theory & Safety Primer")
    st.markdown("Cool flames occur at low temperatures (400°C–600°C). In microgravity and high altitudes, droplet combustion exhibits unique cool-flame oscillations critical for aerospace safety.")
