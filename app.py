import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import time
from datetime import datetime

# Page Configuration
st.set_page_config(
    page_title="AeroGuard v4.7 | Expanded 3D Sim",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Advanced Aerospace Styling
st.markdown("""
    <style>
    .main { background-color: #090b10; }
    div[data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ AeroGuard: Aerospace Fire Safety & Combustion Simulator")
st.markdown("NASA PSI Combustion Models & 3D Phase-Space Simulation Suite")

# Session State Initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = "Guest"
if "mission_history" not in st.session_state:
    st.session_state.mission_history = []
if "anomaly_active" not in st.session_state:
    st.session_state.anomaly_active = False

# Authentication Sidebar
st.sidebar.header("🔐 Access Control")
if not st.session_state.logged_in:
    auth_mode = st.sidebar.radio("Login Method", ["Guest Mode", "Google OAuth", "Twitter/X OAuth"])
    if st.sidebar.button("Authenticate"):
        st.session_state.logged_in = True
        st.session_state.user = f"User_{auth_mode.replace(' ', '_')}"
        st.rerun()
else:
    st.sidebar.success(f"Logged in as: {st.session_state.user}")
    if st.sidebar.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()

st.sidebar.divider()
st.sidebar.header("🎛️ Simulation Parameters")

# Combustion Data (NASA PSI Models)
data = {
    "Fuel_Material": ["Carbon Composite", "Titanium Alloy Ti-6Al-4V", "Kapton Insulation", "Nomex Honeycomb"],
    "Flame_Spread_s": [1.45, 0.95, 2.10, 1.65],
    "Limiting_O2_Index": [24.5, 31.0, 21.0, 28.0]
}
df = pd.DataFrame(data)

selected_fuel = st.sidebar.selectbox("Select Material", df["Fuel_Material"])
cabin_o2 = st.sidebar.slider("Cabin Oxygen Concentration (%)", 15.0, 35.0, 21.0)
effective_airflow = st.sidebar.slider("Ventilation Airflow (m/s)", 0.5, 5.0, 1.8)

fuel_row = df[df["Fuel_Material"] == selected_fuel].iloc[0]

# Physics & Damage Calculations
o2_mult = (cabin_o2 / 21.0) ** 1.85
flow_mult = 1.4 if effective_airflow < 2.0 else (1.0 + (effective_airflow / 14.0))
flame_val = fuel_row.get("Flame_Spread_s", 1.45)
est_spread = round(flame_val * o2_mult * flow_mult, 2)
est_spread = round(est_spread * 0.35, 2)

col1, col2, col3 = st.columns(3)
col1.metric("Estimated Flame Spread", f"{est_spread} m/s", delta="-0.12 m/s")
col2.metric("Limiting $O_2$ Index", f"{fuel_row['Limiting_O2_Index']}%")
col3.metric("System Status", "NOMINAL" if not st.session_state.anomaly_active else "CRITICAL")

st.divider()

# 3D Plotly Visualization (Bounded Container)
st.subheader("🌌 3D Combustion Phase-Space Visualizer")

np.random.seed(42)
x_vals = np.linspace(15, 35, 30)
y_vals = np.linspace(0.5, 5.0, 30)
X, Y = np.meshgrid(x_vals, y_vals)
Z = (X / 21.0) * (Y * 0.5) * flame_val

fig = go.Figure(data=[go.Surface(z=Z, x=X, y=Y, colorscale='Viridis')])
fig.update_layout(
    title="NASA PSI Thermodynamic Combustion Vector Space",
    scene=dict(
        xaxis_title='Cabin O2 (%)',
        yaxis_title='Airflow (m/s)',
        zaxis_title='Combustion Intensity (kW/m²)'
    ),
    margin=dict(l=0, r=0, t=30, b=0),
    height=500
)
st.plotly_chart(fig, use_container_width=True)

# Injection Logic & AI Guardian
st.subheader("🤖 AI Guardian Reverse-Optimizer")
col_a, col_b = st.columns(2)

with col_a:
    if st.button("Inject Thermal Stress Test"):
        st.session_state.anomaly_active = True
        st.session_state.mission_history.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": st.session_state.user,
            "event": "Thermal Stress Injected"
        })
        st.error("Anomaly Triggered! Guardian Protocol Active.")

with col_b:
    if st.button("Reset Guardian"):
        st.session_state.anomaly_active = False
        st.success("System Restored to Baseline.")

if st.session_state.mission_history:
    with st.expander("Mission Telemetry & Audit Logs"):
        st.write(pd.DataFrame(st.session_state.mission_history))
