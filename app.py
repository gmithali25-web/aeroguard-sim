import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import time
# --- MENTOR-BACKED FLIGHT PROFILES & ALTITUDE PHYSICS ---
FLIGHT_PROFILES = {
    "orbital_microgravity": {
        "name": "Orbital Habitation (ISS / Lunar Gateway)",
        "altitude_ft": 250000,
        "external_temp_c": -150.0,
        "dynamic_pressure_kpa": 0.0,
        "vibration_stress_factor": 1.0,
        "description": "Stable orbital environment. Zero aerodynamic drag; internal ECLSS manages life support."
    },
    "max_q_ascent": {
        "name": "Max-Q Transonic Ascent (40,000 ft)",
        "altitude_ft": 40000,
        "external_temp_c": -56.5,
        "dynamic_pressure_kpa": 35.4,
        "vibration_stress_factor": 2.4,
        "description": "Peak dynamic pressure zone. High mechanical stress & severe aerodynamic heat flux."
    },
    "stratosphere_climb": {
        "name": "Stratosphere Cruise (80,000 ft)",
        "altitude_ft": 80000,
        "external_temp_c": -51.0,
        "dynamic_pressure_kpa": 5.1,
        "vibration_stress_factor": 1.5,
        "description": "High-altitude climb. Sub-zero external temperature gradients across the hull."
    },
    "ground_liftoff": {
        "name": "Pad Liftoff & Acoustic Shear (0 ft)",
        "altitude_ft": 0,
        "external_temp_c": 15.0,
        "dynamic_pressure_kpa": 0.0,
        "vibration_stress_factor": 1.0,
        "description": "Initial launch pad phase with high acoustic resonance and structural vibration."
    }
}
from datetime import datetime

# Page Configuration
st.set_page_config(
    page_title="AeroGuard v4.7 | Expanded 3D Box",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Advanced Aerospace Styling
st.markdown("""
    <style>
    .main { background-color: #090b10; }
    div[data-testid="stMetric"] {
        background-color: #131722;
        border: 1px solid #262c3d;
        padding: 12px 16px;
        border-radius: 8px;
    }
    .alarm-banner {
        background: linear-gradient(90deg, #7f1d1d 0%, #dc2626 50%, #7f1d1d 100%);
        color: white; padding: 14px 20px; border-radius: 8px;
        font-weight: 700; text-align: center; letter-spacing: 1px; margin-bottom: 16px;
        border: 1px solid #fca5a5;
    }
    .nominal-banner {
        background: linear-gradient(90deg, #064e3b 0%, #059669 50%, #064e3b 100%);
        color: white; padding: 12px 20px; border-radius: 8px;
        font-weight: 600; text-align: center; letter-spacing: 0.8px; margin-bottom: 16px;
        border: 1px solid #6ee7b7;
    }
    .login-container {
        max-width: 480px;
        margin: 60px auto;
        padding: 40px;
        background-color: #131722;
        border: 1px solid #262c3d;
        border-radius: 12px;
        text-align: center;
    }
    /* Custom Bounded Box for 3D Plot */
    .plot-box-container {
        border: 2px solid #262c3d;
        background-color: #131722;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
    </style>
""", unsafe_allow_html=True)

# Session State Initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "mission_history_db" not in st.session_state:
    st.session_state.mission_history_db = []

# --- MULTI-PROVIDER OAUTH & GUEST LOGIN GATE SCREEN ---
if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        st.markdown("""
            <div class="login-container">
                <h2>🛰️ AeroGuard Gateway</h2>
                <p style="color: #94a3b8; font-size: 14px; margin-bottom: 25px;">Secure Microgravity Fire Safety & Flight Control System</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='max-width: 480px; margin: -70px auto 0 auto; padding: 0 40px;'>", unsafe_allow_html=True)
        
        if st.button("🔑 Continue with Google", use_container_width=True, type="primary"):
            st.session_state.logged_in = True
            st.session_state.user_email = "operator.google@nasa-analogue.org"
            st.rerun()
            
        if st.button("🐦 Continue with Twitter (X)", use_container_width=True):
            st.session_state.logged_in = True
            st.session_state.user_email = "operator.twitter@aeroguard-ops.io"
            st.rerun()

        if st.button("👤 Continue as Guest / Simulator Operator", use_container_width=True):
            st.session_state.logged_in = True
            st.session_state.user_email = "guest.controller@aeroguard.sim"
            st.rerun()
            
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- MAIN APP ---

if "telemetry_history" not in st.session_state:
    np.random.seed(42)
    times = pd.date_range(end=datetime.now(), periods=20, freq="2s")
    st.session_state.telemetry_history = pd.DataFrame({
        "Timestamp": [t.strftime("%H:%M:%S") for t in times],
        "CO_ppm": np.random.normal(1.2, 0.2, 20).clip(0.5, 5.0),
        "Smoke_Obscuration_pct": np.random.normal(0.08, 0.02, 20).clip(0.01, 0.5),
        "Cabin_Temp_C": np.random.normal(22.4, 0.15, 20)
    })

if "anomaly_active" not in st.session_state:
    st.session_state.anomaly_active = False
if "hvac_isolated" not in st.session_state:
    st.session_state.hvac_isolated = False
if "rack_power_cut" not in st.session_state:
    st.session_state.rack_power_cut = False
if "damage_accumulator" not in st.session_state:
    st.session_state.damage_accumulator = 0.0
if "anomaly_start_time" not in st.session_state:
    st.session_state.anomaly_start_time = None
if "fire_duration_sec" not in st.session_state:
    st.session_state.fire_duration_sec = 20

# NASA PSI Combustion Reference Database
@st.cache_data
def load_nasa_psi_database():
    return pd.DataFrame({
        "Mission_ID": ["FLEX-01", "BASS-02", "SPICE-01", "SAME-R", "FLEX-02", "Saffire-IV", "BASS-M", "FLEX-ICE", "ACME-E", "Saffire-V"],
        "Fuel_Material": [
            "Gaseous Propane", "Solid PMMA (Acrylic)", "Methane Jet", 
            "ETFE Wire Insulation", "Ethanol Droplet", "Cotton-Fiberglass Nomex", 
            "Cast PMMA Rod", "n-Heptane Droplet", "Ethylene Coflow", "Silicone Composite"
        ],
        "Class": ["Hydrocarbon Gas", "Thermoplastic", "Hydrocarbon Gas", "Avionics Wiring", "Liquid Propellant", "Crew Fabric", "Thermoplastic", "Liquid Fuel", "Gas Jet", "Sealant/Polymer"],
        "Oxygen_Pct": [18.0, 30.0, 21.0, 24.5, 35.0, 26.0, 22.0, 28.0, 23.5, 32.0],
        "Airflow_cm_s": [5.0, 10.2, 2.1, 0.8, 15.0, 12.0, 1.5, 4.0, 6.5, 8.0],
        "Flame_Spread_mm_s": [3.2, 14.8, 4.5, 1.9, 22.4, 18.5, 2.8, 11.2, 7.6, 13.4],
        "Radiative_Flux_kW_m2": [12.5, 45.0, 18.2, 9.4, 58.0, 38.5, 14.0, 32.1, 21.0, 36.8],
        "Limiting_O2_Index": [15.5, 17.8, 16.2, 19.0, 14.8, 20.5, 18.2, 15.2, 16.0, 21.0],
        "Quench_Difficulty": ["Low", "High", "Moderate", "Moderate", "Critical", "High", "Low", "High", "Moderate", "High"]
    })

df = load_nasa_psi_database()

# Sidebar Controls
    st.sidebar.markdown("---")
    st.sidebar.subheader("🚀 Mission Flight Phase")
    
    selected_phase_key = st.sidebar.selectbox(
        "Select Ascent / Orbital Phase",
        options=list(FLIGHT_PROFILES.keys()),
        format_func=lambda x: FLIGHT_PROFILES[x]["name"],
        index=0
    )
    
    active_profile = FLIGHT_PROFILES[selected_phase_key]

st.sidebar.markdown(f"## 🛰️ GUARDIAN CONTROLLER")
st.sidebar.markdown(f"**Authenticated Account:**\n`{st.session_state.user_email}`")
if st.sidebar.button("🚪 Logout / Switch Account", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.user_email = ""
    st.rerun()

st.sidebar.markdown("---")
target_module = st.sidebar.selectbox("Active Habitat Module", ["ISS - Destiny Laboratory", "ISS - Harmony Node 2", "Lunar Gateway - HALO", "Orion Crew Capsule"])
selected_fuel = st.sidebar.selectbox("Primary Fuel / Surface Material", df["Fuel_Material"].unique())

cabin_o2 = st.sidebar.number_input("Ambient Oxygen ($O_2$ %)", min_value=10.0, max_value=50.0, value=24.5, step=0.5)
cabin_airflow = st.sidebar.number_input("Ventilation Velocity ($cm/s$)", min_value=0.0, max_value=50.0, value=6.5, step=0.5)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ Live Telemetry & Damage Drills")
live_stream = st.sidebar.toggle("🔴 Enable Live Sensor Stream", value=False)

fire_duration_sec = st.sidebar.selectbox(
    "⏱️ Fire Drill Duration (Seconds)",
    [10, 20, 30, 45, 60],
    index=1
)
st.session_state.fire_duration_sec = fire_duration_sec

col_b1, col_b2 = st.sidebar.columns(2)
inject_clicked = col_b1.button("🔥 Inject Fire Anomaly", use_container_width=True)
reset_clicked = col_b2.button("🔄 Reset Guardian", use_container_width=True)

# Physics & Damage Calculations
fuel_row = df[df["Fuel_Material"] == selected_fuel].iloc[0]
effective_airflow = 0.2 if st.session_state.hvac_isolated else cabin_airflow
loi_margin = round(cabin_o2 - fuel_row["Limiting_O2_Index"], 1)

flow_mult = 1.4 if effective_airflow < 2.0 else (1.0 + (effective_airflow / 14.0))
o2_mult = (cabin_o2 / 21.0) ** 1.85
est_spread = round(fuel_row["Flame_Spread_mm_s"] * o2_mult * flow_mult, 2)
if st.session_state.rack_power_cut:
    est_spread = round(est_spread * 0.35, 2)

# --- INJECTION LOGIC ---
if inject_clicked:
    st.session_state.anomaly_active = True
    st.session_state.anomaly_start_time = time.time()

if reset_clicked:
    if st.session_state.damage_accumulator > 0:
        st.session_state.mission_history_db.append({
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "User": st.session_state.user_email,
            "Module": target_module,
            "Material": selected_fuel,
            "Oxygen_Pct": cabin_o2,
            "Airflow_cm_s": cabin_airflow,
            "Final_Damage_Pct": round(st.session_state.damage_accumulator, 1),
            "Structural_Integrity_Pct": round(100.0 - st.session_state.damage_accumulator, 1),
            "Status": "Completed / Reset"
        })
    st.session_state.anomaly_active = False
    st.session_state.rack_power_cut = False
    st.session_state.hvac_isolated = False
    st.session_state.damage_accumulator = 0.0
    st.session_state.anomaly_start_time = None

# Timer calculation & live accumulation
time_remaining = 0
if st.session_state.anomaly_active and st.session_state.anomaly_start_time:
    time_elapsed = int(time.time() - st.session_state.anomaly_start_time)
    time_remaining = max(0, st.session_state.fire_duration_sec - time_elapsed)
    
    if not st.session_state.rack_power_cut:
        st.session_state.damage_accumulator = min(100.0, st.session_state.damage_accumulator + (est_spread * 0.12))
    
    if time_elapsed >= st.session_state.fire_duration_sec:
        st.session_state.anomaly_active = False
        st.session_state.mission_history_db.append({
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "User": st.session_state.user_email,
            "Module": target_module,
            "Material": selected_fuel,
            "Oxygen_Pct": cabin_o2,
            "Airflow_cm_s": cabin_airflow,
            "Final_Damage_Pct": round(st.session_state.damage_accumulator, 1),
            "Structural_Integrity_Pct": round(100.0 - st.session_state.damage_accumulator, 1),
            "Status": "Drill Finished"
        })

damage_pct = round(st.session_state.damage_accumulator, 1)
structural_integrity = round(max(0.0, 100.0 - damage_pct), 1)

latest_co = st.session_state.telemetry_history["CO_ppm"].iloc[-1]
latest_smoke = st.session_state.telemetry_history["Smoke_Obscuration_pct"].iloc[-1]

# Header & Alert Banner
st.title("🛰️ AeroGuard: Autonomous Microgravity Fire Guardian")
st.markdown(f"**Guardian Status:** Active Monitoring `{target_module}` | **Material Protection:** `{selected_fuel}`")

if st.session_state.anomaly_active:
    st.markdown(f"""
        <div class="alarm-banner">
            🚨 LIVE DRILL ACTIVE: TIME REMAINING: {time_remaining}s / {st.session_state.fire_duration_sec}s — DAMAGE: {damage_pct}% | INTEGRITY: {structural_integrity}%
        </div>
    """, unsafe_allow_html=True)
elif damage_pct > 15.0:
    st.markdown(f"""
        <div class="alarm-banner">
            🚨 STRUCTURAL HAZARD ALERT: DAMAGE: {damage_pct}% | INTEGRITY: {structural_integrity}%
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
        <div class="nominal-banner">
            ✅ GUARDIAN NOMINAL: SURFACE INTEGRITY AT 100% — READY FOR DRILL
        </div>
    """, unsafe_allow_html=True)

# Top KPIs
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Drill Timer Status", f"{time_remaining}s Left" if st.session_state.anomaly_active else "Ready", f"Duration: {st.session_state.fire_duration_sec}s")
k2.metric("Surface Damage Extent", f"{damage_pct}%", f"{est_spread} mm/s Spread", delta_color="inverse")
k3.metric("Structural Integrity", f"{structural_integrity}%", "Safe" if structural_integrity > 75 else "FAIL RISK", delta_color="normal" if structural_integrity > 75 else "inverse")
k4.metric("Live CO Sensor", f"{latest_co} ppm", "CRITICAL" if latest_co > 15 else "Nominal", delta_color="inverse" if latest_co > 15 else "normal")
k5.metric("Radiative Heat Flux", f"{round(fuel_row['Radiative_Flux_kW_m2'] * o2_mult, 1)} kW/m²", "Thermal Load")

st.markdown("<br>", unsafe_allow_html=True)

# Tabs
tab_damage, tab_live, tab_3d, tab_control, tab_history, tab_ai = st.tabs([
    "🛡️ Surface & Structural Damage Assessment",
    "📡 Live Sensor Stream",
    "🧊 3D Flammability Phase Space",
    "🎛️ Automated Suppression Overrides",
    "📜 Mission Logs & History",
    "🤖 AI Guardian Physicist & Reverse Optimizer"
])

# TAB 1: Surface & Structural Damage Assessment
with tab_damage:
    st.subheader(f"Thermal Degradation & Surface Impact Analysis: `{selected_fuel}`")
    st.markdown("Real-time simulation of pyrolytic mass loss, surface charring depth, and structural load failure during microgravity combustion.")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.markdown("### 📋 Material Degradation Metrics")
        st.write(f"- **Target Material Class:** `{fuel_row['Class']}`")
        st.write(f"- **Cumulative Surface Burn Area:** `{round(damage_pct * 1.4, 1)} cm²`")
        st.write(f"- **Estimated Pyrolysis Depth:** `{round(damage_pct * 0.08, 2)} mm` into bulkhead/rack substrate.")
        st.write(f"- **Active Drill Countdown:** `{time_remaining} seconds remaining`")
        
        if damage_pct < 10:
            st.success("🟢 **Surface Status:** Nominal. Minor thermal reflection only. No structural compromise.")
        elif damage_pct < 40:
            st.warning("🟠 **Surface Status:** Moderate Charring. Surface polymer bonds breaking down. Prepare local extinguishers.")
        else:
            st.error("🔴 **Surface Status:** CRITICAL FAILURE RISK. Subsurface structural panel weakening. Immediate power cutoff and water-mist required!")

    with col_d2:
        st.markdown("### 📊 Structural Integrity Monitoring")
        st.markdown(f"**Remaining Load Capacity:** `{structural_integrity}%`")
        st.progress(int(structural_integrity))
        
        if structural_integrity > 75:
            st.info("✅ **Assessment:** Habitat structural envelope is fully secure against current thermal loads.")
        elif structural_integrity > 40:
            st.warning("⚠️ **Assessment:** Elevated thermal fatigue. Monitor boundary layer temperatures closely.")
        else:
            st.error("🚨 **Assessment:** CRITICAL FAILURE IMMINENT. Bulkhead structural integrity compromised.")

# TAB 2: Live Sensor Stream
with tab_live:
    st.subheader(f"Real-Time Multi-Gas & Optical Smoke Telemetry ({target_module})")
    fig_live = go.Figure()
    fig_live.add_trace(go.Scatter(x=st.session_state.telemetry_history["Timestamp"], y=st.session_state.telemetry_history["CO_ppm"], mode="lines+markers", name="Carbon Monoxide (ppm)", line=dict(color="#ef4444", width=3)))
    fig_live.add_trace(go.Scatter(x=st.session_state.telemetry_history["Timestamp"], y=st.session_state.telemetry_history["Smoke_Obscuration_pct"] * 10, mode="lines+markers", name="Smoke Index (x10)", line=dict(color="#38bdf8", width=2, dash="dot")))
    fig_live.update_layout(template="plotly_dark", height=350, xaxis_title="UTC Time", yaxis_title="Amplitude")
    st.plotly_chart(fig_live, use_container_width=True)

# TAB 3: 3D Phase Space (UPDATED WITH VERTICAL BOUNDED BOX & SCROLL ZOOM)
with tab_3d:
    st.subheader("3D Microgravity Combustion Risk Envelope")
    st.markdown("Interactive phase space mapping ventilation velocity, oxygen levels, and radiative heat flux against material quench difficulty.")
    
    st.markdown('<div class="plot-box-container">', unsafe_allow_html=True)
    
    fig_3d = px.scatter_3d(
        df, 
        x="Airflow_cm_s", 
        y="Oxygen_Pct", 
        z="Radiative_Flux_kW_m2", 
        color="Quench_Difficulty", 
        size="Flame_Spread_mm_s", 
        hover_name="Mission_ID", 
        color_discrete_map={"Low": "#10b981", "Moderate": "#f59e0b", "High": "#ef4444", "Critical": "#a855f7"}
    )
    fig_3d.update_layout(
        template="plotly_dark", 
        height=550, 
        scene=dict(
            xaxis_title="Airflow (cm/s)",
            yaxis_title="Oxygen %",
            zaxis_title="Radiative Flux (kW/m²)"
        ),
        margin=dict(l=0, r=0, b=0, t=30)
    )
    st.plotly_chart(fig_3d, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# TAB 4: Hardware Overrides
with tab_control:
    st.subheader("🎛️ Automated Suppression & Hardware Interlocks")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Toggle HVAC Damper Isolation", type="primary" if not st.session_state.hvac_isolated else "secondary"):
            st.session_state.hvac_isolated = not st.session_state.hvac_isolated
            st.rerun()
        st.info(f"HVAC: {'ISOLATED' if st.session_state.hvac_isolated else 'ACTIVE'}")
    with c2:
        if st.button("Execute Rack Power Cutoff", type="primary" if not st.session_state.rack_power_cut else "secondary"):
            st.session_state.rack_power_cut = not st.session_state.rack_power_cut
            st.rerun()
        st.info(f"Power: {'DE-ENERGIZED' if st.session_state.rack_power_cut else 'ON'}")
    with c3:
        if st.button("Trigger Fine Water-Mist Suppressor"):
            st.session_state.anomaly_active = False
            st.success("✅ Water-mist quenched thermal flux. Surface damage progression halted.")

# TAB 5: Mission Logs & History
with tab_history:
    st.subheader(f"📜 Flight Controller Audit Trail & History: `{st.session_state.user_email}`")
    st.markdown("All completed fire anomaly drills, input parameters, and resulting structural damage are securely recorded here.")
    
    user_logs_indexed = [
        (idx, log) for idx, log in enumerate(st.session_state.mission_history_db) 
        if log["User"] == st.session_state.user_email
    ]
    
    if user_logs_indexed:
        df_history = pd.DataFrame([log for _, log in user_logs_indexed])
        st.dataframe(df_history, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🗑️ Clean Up / Delete Specific Mission Records")
        
        selected_indices_to_delete = st.multiselect(
            "Select specific mission records to remove:",
            options=[item[0] for item in user_logs_indexed],
            format_func=lambda idx: f"[{st.session_state.mission_history_db[idx]['Timestamp']}] {st.session_state.mission_history_db[idx]['Module']} ({st.session_state.mission_history_db[idx]['Material']}) - Damage: {st.session_state.mission_history_db[idx]['Final_Damage_Pct']}%"
        )
        
        col_del1, col_del2 = st.columns([1, 4])
        if col_del1.button("🗑️ Delete Selected Records", type="primary"):
            if selected_indices_to_delete:
                st.session_state.mission_history_db = [
                    log for i, log in enumerate(st.session_state.mission_history_db)
                    if i not in selected_indices_to_delete
                ]
                st.success("Selected mission records successfully deleted!")
                time.sleep(0.8)
                st.rerun()
            else:
                st.warning("Please select at least one record to delete.")
    else:
        st.info("ℹ️ No mission logs recorded yet for this account. Run a fire drill to save your first entry!")

# TAB 6: AI Guardian Physicist & Reverse Optimizer
with tab_ai:
    st.subheader("🤖 AI Guardian Physicist & Reverse Parameter Optimizer")
    st.markdown("Provide your **desired safety output** (maximum allowable damage %), and the AI will reverse-calculate the safe operating inputs for your chosen habitat and material.")
    
    col_ai1, col_ai2 = st.columns(2)
    
    with col_ai1:
        st.markdown("### 🎯 Target Output Requirements")
        target_max_damage = st.number_input(
            "Max Allowable Surface Damage (%)", 
            min_value=0.1, 
            max_value=100.0, 
            value=10.0, 
            step=1.0,
            format="%.1f"
        )
        target_eval_material = st.selectbox("Select Material for Reverse Analysis", df["Fuel_Material"].unique(), key="rev_mat")
        target_eval_module = st.selectbox("Select Habitat Module", ["ISS - Destiny Laboratory", "ISS - Harmony Node 2", "Lunar Gateway - HALO", "Orion Crew Capsule"], key="rev_mod")
        
        mat_row = df[df["Fuel_Material"] == target_eval_material].iloc[0]
        max_safe_o2 = round(mat_row["Limiting_O2_Index"] + (target_max_damage / 15.0), 1)
        max_safe_airflow = round(max(0.5, 12.0 - (target_max_damage * 0.2)), 1)
        
        calculate_inputs = st.button("✨ Reverse-Engineer Safe Inputs", type="primary", use_container_width=True)

    with col_ai2:
        st.markdown("### 📋 AI Recommended Safe Inputs")
        if calculate_inputs:
            st.success("Optimization Complete! Recommended environment parameters:")
            st.write(f"- **Target Habitat Module:** `{target_eval_module}`")
            st.write(f"- **Evaluated Material:** `{target_eval_material}` (`{mat_row['Class']}`)")
            st.write(f"- **Maximum Allowable Damage:** `{target_max_damage}%`")
            st.markdown("---")
            st.markdown(f"### 🛡️ Recommended Virtual Inputs:")
            st.info(f"🟢 **Max Safe Ambient Oxygen ($O_2$):** `≤ {max_safe_o2}%`")
            st.info(f"🟢 **Optimal Ventilation Velocity:** `≤ {max_safe_airflow} cm/s`")
            st.warning(f"💡 **AI Note:** Operating above `{max_safe_o2}% O₂` with `{target_eval_material}` risks exceeding your `{target_max_damage}%` damage threshold during a thermal anomaly.")
        else:
            st.info("👈 Type your target damage threshold into the text box and click **'Reverse-Engineer Safe Inputs'** to generate AI recommendations.")

if live_stream and st.session_state.anomaly_active:
    time.sleep(1.0)
    st.rerun()
