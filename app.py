from __future__ import annotations

import hashlib
import io
import zipfile
from datetime import datetime, timezone
from pathlib import PurePosixPath

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import pydeck as pdk
import streamlit as st


# ============================================================
# AEROGUARD SIM — research-first aerospace fire-safety platform
# ============================================================

st.set_page_config(
    page_title="AeroGuard Sim | Aerospace Research Lab",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap');
    :root { --bg:#050d1b; --panel:#0a1b30; --line:#173653; --cyan:#22d3ee;
            --teal:#19d3b0; --muted:#91a9c2; --white:#edf6ff; }
    .stApp {background:radial-gradient(ellipse at 50% 0%,#0b2340 0%,#050d1b 58%);color:var(--white);}
    html,body,[class*="css"] {font-family:Inter,sans-serif;}
    section[data-testid="stSidebar"] {background:#061326;border-right:1px solid var(--line);}
    section[data-testid="stSidebar"] * {color:#d8e8f7;}
    .block-container {padding-top:1.1rem;max-width:1800px;}
    .hero {padding:22px 24px;border:1px solid #1c4565;border-radius:16px;
           background:linear-gradient(120deg,rgba(9,34,59,.98),rgba(5,16,31,.94));}
    .eyebrow {font:700 .68rem 'Space Mono';letter-spacing:.18em;color:var(--cyan);}
    .hero h1 {font-size:2rem;margin:.35rem 0;color:#f4f9ff;}
    .hero p {color:#9bb4cd;margin:0;}
    .panel {padding:16px 18px;border:1px solid var(--line);border-radius:13px;
            background:linear-gradient(145deg,rgba(12,32,55,.97),rgba(6,19,36,.98));}
    .muted {color:var(--muted);font-size:.82rem;}
    .kpi {padding:13px 15px;border:1px solid #1b4263;border-radius:11px;
          background:linear-gradient(145deg,#0c2340,#08172a);min-height:90px;}
    .kpi-label {font-size:.67rem;letter-spacing:.1em;text-transform:uppercase;color:#91a9c2;}
    .kpi-value {font:700 1.25rem 'Space Mono';color:#f1f8ff;margin-top:7px;}
    div[data-testid="stMetric"] {background:#0b2038;border:1px solid #173653;padding:10px 12px;border-radius:10px;}
    div[data-testid="stMetricLabel"] {color:#91a9c2;}
    div[data-testid="stMetricValue"] {color:#f1f8ff;font-family:'Space Mono';}
    .stButton>button,.stDownloadButton>button {background:#073b50;border:1px solid #167d96;color:#e2fbff;border-radius:8px;}
    footer {visibility:hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# NASA SLS Block 1 published reference values. Not a full vehicle CAD model.
SLS = {
    "vehicle_height_m": 98.3,
    "core_height_m": 64.6,
    "core_diameter_m": 8.4,
    "core_empty_mass_kg": 85275,
    "launch_thrust_kN": 36786,
    "max_thrust_kN": 39144,
    "boosters": 2,
    "rs25": 4,
    "booster_burn_s": 126,
    "core_burn_s": 480,
}
NASA_SLS_URL = "https://www.nasa.gov/reference/sls-space-launch-system-core-stage/"
NASA_SLS_GUIDE = "https://www.nasa.gov/wp-content/uploads/2022/03/sls-reference-guide-2022-v2-508-0.pdf"
PSI_URL = "https://psi.nasa.gov/physci/repo/search?data_source=psi&data_type=investigation"
STUDY_ID = "PSI-117"
STUDY_TITLE = "Effect of External Thermo-Convective Perturbation on Cool Flame Dynamics: A Multidimensional Multi-Physics CFD Analysis"

FLIGHT_PHASES = {
    "Pad / ignition": {"altitude_km": 0.0, "description": "Pre-launch and ignition context. Ground-level boundary conditions are site-dependent."},
    "Early ascent": {"altitude_km": 15.0, "description": "Illustrative early-ascent state; aerodynamic and acoustic loads require vehicle-specific models."},
    "Max-Q region": {"altitude_km": 11.0, "description": "Maximum dynamic pressure is trajectory-dependent; this preset is conceptual, not a flight prediction."},
    "Upper ascent": {"altitude_km": 60.0, "description": "Upper-atmosphere region with rapidly changing density and external heat-transfer conditions."},
    "Core-stage cutoff": {"altitude_km": 160.0, "description": "Reference stage-separation context; actual altitude varies by mission and trajectory."},
}
LAUNCH_SITES = {
    "Kennedy Space Center, LC-39B": (28.573, -80.649),
    "Vandenberg Space Force Base": (34.742, -120.572),
    "Wallops Flight Facility": (37.940, -75.466),
    "Satish Dhawan Space Centre": (13.719, 80.230),
    "Custom coordinates": (28.573, -80.649),
}

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def read_table(name: str, raw: bytes) -> pd.DataFrame:
    low = name.lower()
    if low.endswith(".csv"):
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return pd.read_csv(io.BytesIO(raw), encoding=enc)
            except Exception:
                pass
        raise ValueError("Could not decode CSV.")
    if low.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(raw))
    raise ValueError("Unsupported table format.")

def load_uploaded_bundle(files):
    records, tables, text_files = [], [], []
    for f in files:
        raw = f.getvalue()
        records.append({
            "File": f.name, "Bytes": len(raw), "SHA-256": sha256(raw),
            "Uploaded UTC": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        if f.name.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                for member in zf.infolist():
                    if member.is_dir():
                        continue
                    # Avoid extracting files; only read supported members in memory.
                    content = zf.read(member)
                    suffix = PurePosixPath(member.filename).suffix.lower()
                    label = f"{f.name} :: {member.filename}"
                    if suffix in (".csv", ".xlsx", ".xls"):
                        try:
                            tables.append((label, read_table(member.filename, content), sha256(content)))
                        except Exception as exc:
                            text_files.append((label, f"Table read error: {exc}"))
                    elif suffix in (".txt", ".md", ".json", ".yaml", ".yml"):
                        text_files.append((label, content.decode("utf-8", errors="replace")[:200000]))
        elif f.name.lower().endswith((".csv", ".xlsx", ".xls")):
            tables.append((f.name, read_table(f.name, raw), sha256(raw)))
        else:
            text_files.append((f.name, raw.decode("utf-8", errors="replace")[:200000]))
    return records, tables, text_files

def kpi(label, value, note=""):
    st.markdown(
        f'<div class="kpi"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div><div class="muted">{note}</div></div>',
        unsafe_allow_html=True,
    )

def rocket_figure(explode: bool = False):
    """Schematic interactive 3D SLS-like Block 1 layout; not engineering CAD."""
    fig = go.Figure()
    # Vertical axis is normalized to vehicle height. Components are intentionally schematic.
    def cylinder(name, x, y, z0, z1, radius, color, opacity=1.0):
        theta = np.linspace(0, 2*np.pi, 36)
        z = np.linspace(z0, z1, 18)
        T, Z = np.meshgrid(theta, z)
        X, Y = radius*np.cos(T)+x, radius*np.sin(T)+y
        fig.add_trace(go.Surface(
            x=X, y=Y, z=Z, surfacecolor=np.zeros_like(Z),
            colorscale=[[0,color],[1,color]], showscale=False, opacity=opacity,
            name=name, hovertemplate=f"<b>{name}</b><extra></extra>",
        ))
        # Top and bottom caps
        for zz in (z0, z1):
            fig.add_trace(go.Scatter3d(
                x=x+radius*np.cos(theta), y=y+radius*np.sin(theta),
                z=np.full_like(theta, zz), mode="lines",
                line=dict(color=color,width=2), showlegend=False, hoverinfo="skip"
            ))
    shift = 7 if explode else 0
    cylinder("Core stage / LH2 + LOX tanks", 0, 0, 16, 80, 1.0, "#e58a43")
    cylinder("Forward skirt / intertank", 0, 0, 80, 86, 1.02, "#aebdca")
    cylinder("Orion / upper stack (schematic)", 0, 0, 86, 98.3, .65, "#d8e6f2")
    cylinder("Left solid rocket booster", -1.48-shift*.05, 0, 14, 83, .28, "#d7dce3")
    cylinder("Right solid rocket booster", 1.48+shift*.05, 0, 14, 83, .28, "#d7dce3")
    # Engine section and four RS-25 nozzle hints
    for x in (-.42, .42):
        for y in (-.42, .42):
            cylinder("RS-25 engine (one of four)", x, y, 8, 16, .17, "#6f879e")
    fig.update_layout(
        height=650, margin=dict(l=0,r=0,t=20,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#d9e9f8"),
        scene=dict(
            bgcolor="rgba(0,0,0,0)", aspectmode="manual",
            aspectratio=dict(x=1,y=1,z=2.7),
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            zaxis=dict(title="Schematic height (m)", color="#91a9c2", range=[0,105]),
            camera=dict(eye=dict(x=1.8,y=1.8,z=1.25)),
        ),
        showlegend=False,
    )
    return fig

def trajectory_figure(progress: float):
    # Illustration only: a smooth curved path, not an integrated trajectory solver.
    t = np.linspace(0, max(progress, 0.001), 160)
    x = 0.12*t + 0.0007*t*t
    z = 0.025*t + 0.00013*t*t
    fig = go.Figure()
    fig.add_trace(go.Scatter3d(x=x,y=np.zeros_like(x),z=z,mode="lines",
                               line=dict(color="#22d3ee",width=6),name="Illustrative path"))
    fig.add_trace(go.Scatter3d(x=[x[-1]],y=[0],z=[z[-1]],mode="markers",
                               marker=dict(size=7,color="#ff9b52"),name="Vehicle marker"))
    fig.update_layout(
        height=430, margin=dict(l=0,r=0,t=15,b=0),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#d9e9f8"),
        scene=dict(bgcolor="rgba(0,0,0,0)",xaxis=dict(visible=False),
                   yaxis=dict(visible=False),zaxis=dict(visible=False),
                   aspectmode="data"),
        showlegend=False,
    )
    return fig

def map_view(lat, lon):
    frame = pd.DataFrame({"name":["Selected launch location"],"lat":[lat],"lon":[lon]})
    layer = pdk.Layer(
        "ScatterplotLayer", data=frame, get_position="[lon, lat]",
        get_radius=45000, get_fill_color=[34,211,238,210],
        get_line_color=[255,255,255,230], line_width_min_pixels=2,
        pickable=True,
    )
    view = pdk.ViewState(latitude=lat, longitude=lon, zoom=4, pitch=35)
    st.pydeck_chart(pdk.Deck(
        layers=[layer], initial_view_state=view,
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        tooltip={"text":"{name}"},
    ), use_container_width=True)

# Session state
for key, default in {
    "uploaded_records": [], "uploaded_tables": [], "uploaded_text": [],
    "processed_names": set(),
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Sidebar
with st.sidebar:
    st.markdown("## 🚀 AEROGUARD SIM")
    st.caption("RESEARCH • SIMULATION • LEARNING")
    mode = st.radio("Workspace", ["Research Command", "Interactive Learning Lab"])
    if mode == "Research Command":
        page = st.radio("Research modules", [
            "Mission overview & 3D vehicle",
            "Launch environment & trajectory",
            "PSI-117 dataset explorer",
            "Data quality & provenance",
            "Launch site explorer",
        ])
    else:
        page = st.radio("Learning modules", [
            "Combustion parameter lab",
            "Combustion theory & safety",
        ])
    st.divider()
    st.caption("Research reference: NASA PSI-117")
    st.caption("Vehicle reference: NASA SLS Block 1")
    st.caption("Models are educational unless explicitly validated.")

# Main hero
st.markdown(
    '<div class="hero"><div class="eyebrow">AEROGUARD / FLIGHT & FIRE SAFETY INTELLIGENCE</div>'
    '<h1>Explore the physics behind safer spaceflight.</h1>'
    '<p>A research workspace connecting microgravity combustion evidence, aerospace environments and transparent simulation assumptions.</p></div>',
    unsafe_allow_html=True,
)
st.write("")

if page == "Mission overview & 3D vehicle":
    st.subheader("Mission overview")
    a,b,c,d = st.columns(4)
    with a: kpi("Research investigation", "PSI-117", "NASA Physical Sciences Informatics")
    with b: kpi("Reference vehicle", "SLS Block 1", "Published NASA vehicle configuration")
    with c: kpi("Vehicle height", "98.3 m", "NASA SLS reference guide")
    with d: kpi("Launch thrust", "36,786 kN", "Approximate SLS Block 1 launch thrust")
    st.write("")
    left,right = st.columns([1.6,1])
    with left:
        st.markdown("### Interactive 3D vehicle explorer")
        exploded = st.toggle("Exploded component spacing", value=False)
        st.plotly_chart(rocket_figure(exploded), use_container_width=True)
        st.caption("Schematic 3D representation for orientation and teaching. It is not a dimensionally complete CAD model or flight-certified configuration.")
    with right:
        st.markdown("### Vehicle reference data")
        st.metric("Core stage height", "64.6 m")
        st.metric("Core stage diameter", "8.4 m")
        st.metric("RS-25 engines", "4")
        st.metric("Five-segment solid boosters", "2")
        st.markdown("**Major core-stage sections**")
        st.markdown("- Forward skirt and avionics\n- Liquid oxygen (LOX) tank\n- Intertank\n- Liquid hydrogen (LH2) tank\n- Engine section and four RS-25 engines")
        st.markdown(f"[NASA SLS Core Stage reference]({NASA_SLS_URL})")
        st.markdown(f"[NASA SLS Reference Guide (PDF)]({NASA_SLS_GUIDE})")
    st.info("AeroGuard's combustion research focus remains PSI-117/FLEX-derived cool-flame and thermo-convective behaviour. SLS is a separate vehicle-context layer; PSI-117 droplet-fuel data must not be treated as SLS propellant-performance data.")

elif page == "Launch environment & trajectory":
    st.subheader("Launch environment explorer")
    st.caption("Scenario presets provide context only. This page does not solve a launch vehicle's six-degree-of-freedom trajectory.")
    phase_name = st.selectbox("Scenario phase", list(FLIGHT_PHASES))
    phase = FLIGHT_PHASES[phase_name]
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Scenario altitude", f"{phase['altitude_km']:.1f} km")
    with c2: st.metric("Vehicle reference", "SLS Block 1")
    with c3: st.metric("Model status", "Illustrative")
    st.markdown(f'<div class="panel">{phase["description"]}</div>', unsafe_allow_html=True)
    progress = st.slider("Illustrative animation progress", 0, 100, 35, 1)
    st.plotly_chart(trajectory_figure(progress), use_container_width=True)
    st.caption("The curve is a visual placeholder. No thrust integration, mass depletion, gravity turn, atmospheric drag, wind, staging logic or guidance law is computed.")
    st.markdown("### Environmental inputs")
    x,y,z = st.columns(3)
    with x: ambient_temp = st.slider("Ambient temperature (°C)", -100, 40, -20)
    with y: pressure_kpa = st.slider("Ambient pressure (kPa)", 0, 105, 80)
    with z: wind_ms = st.slider("Crosswind speed (m/s)", 0, 40, 5)
    st.write(f"Selected scenario inputs: **{ambient_temp} °C**, **{pressure_kpa} kPa**, **{wind_ms} m/s**.")
    st.warning("These inputs are recorded as scenario settings only. No validated thermal-load or structural-safety conclusion is calculated from them.")

elif page == "PSI-117 dataset explorer":
    st.subheader("NASA PSI-117 research context")
    st.write(STUDY_TITLE)
    st.markdown(f"[Open NASA PSI repository]({PSI_URL})")
    st.info("The supplied source code referenced an Excel workbook, but that workbook was not included with the code file. The table below is therefore not fabricated: upload the actual PSI-117 workbook or exported data to inspect it here.")
    dataset_files = st.file_uploader("Upload PSI-117 data (CSV, XLSX, XLS or ZIP)", type=["csv","xlsx","xls","zip"], accept_multiple_files=True, key="psi_upload")
    if dataset_files:
        new_files = [f for f in dataset_files if f.name not in st.session_state.processed_names]
        if new_files:
            records,tables,texts = load_uploaded_bundle(new_files)
            st.session_state.uploaded_records.extend(records)
            st.session_state.uploaded_tables.extend(tables)
            st.session_state.uploaded_text.extend(texts)
            st.session_state.processed_names.update(f.name for f in new_files)
    if st.session_state.uploaded_tables:
        names = [name for name,_,_ in st.session_state.uploaded_tables]
        chosen = st.selectbox("Select uploaded table", names)
        item = next(x for x in st.session_state.uploaded_tables if x[0] == chosen)
        df = item[1]
        st.caption(f"Source: {chosen} · SHA-256: {item[2]}")
        st.dataframe(df, use_container_width=True, hide_index=True)
        numeric = df.select_dtypes(include=np.number).columns.tolist()
        if numeric:
            col = st.selectbox("Plot numeric variable", numeric)
            plot_df = df[[col]].dropna().reset_index(names="Row")
            st.plotly_chart(px.line(plot_df, x="Row", y=col, title=f"{col} by row"), use_container_width=True)
        st.download_button("Download selected table as CSV", df.to_csv(index=False).encode("utf-8"), file_name="aeroguard_selected_data.csv", mime="text/csv")
    else:
        st.warning("No experimental table loaded yet. Please upload the original source data before drawing scientific conclusions.")
    if st.session_state.uploaded_text:
        with st.expander("Read accompanying text / metadata"):
            for name,content in st.session_state.uploaded_text:
                st.markdown(f"**{name}**")
                st.text(content[:12000])

elif page == "Data quality & provenance":
    st.subheader("Data quality and provenance audit")
    files = st.file_uploader("Upload research files for hashing and inspection", type=["csv","xlsx","xls","zip","txt","md","json"], accept_multiple_files=True, key="audit_upload")
    if files:
        new_files = [f for f in files if f.name not in st.session_state.processed_names]
        if new_files:
            records,tables,texts = load_uploaded_bundle(new_files)
            st.session_state.uploaded_records.extend(records)
            st.session_state.uploaded_tables.extend(tables)
            st.session_state.uploaded_text.extend(texts)
            st.session_state.processed_names.update(f.name for f in new_files)
    if st.session_state.uploaded_records:
        audit = pd.DataFrame(st.session_state.uploaded_records)
        st.dataframe(audit, use_container_width=True, hide_index=True)
        st.download_button("Export provenance log", audit.to_csv(index=False).encode(), "aeroguard_provenance_log.csv", "text/csv")
    else:
        st.info("No files audited in this session.")
    if st.session_state.uploaded_tables:
        st.markdown("### Imported table inventory")
        inventory = pd.DataFrame([{"Source":n,"Rows":len(df),"Columns":len(df.columns),"SHA-256":digest} for n,df,digest in st.session_state.uploaded_tables])
        st.dataframe(inventory, use_container_width=True, hide_index=True)
        st.markdown("### Missing-value summary")
        chosen = st.selectbox("Choose table for quality checks", [n for n,_,_ in st.session_state.uploaded_tables])
        df = next(x[1] for x in st.session_state.uploaded_tables if x[0] == chosen)
        missing = pd.DataFrame({"Column":df.columns,"Missing values":df.isna().sum().values,"Missing (%)":(df.isna().mean().values*100).round(2)})
        st.dataframe(missing, use_container_width=True, hide_index=True)

elif page == "Launch site explorer":
    st.subheader("Launch site locator")
    site = st.selectbox("Choose a launch site", list(LAUNCH_SITES))
    default_lat,default_lon = LAUNCH_SITES[site]
    c1,c2 = st.columns(2)
    with c1: lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=float(default_lat), step=0.001, format="%.4f")
    with c2: lon = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=float(default_lon), step=0.001, format="%.4f")
    map_view(lat,lon)
    st.caption(f"Selected coordinates: {lat:.4f}°, {lon:.4f}°. The map pin is user-selected; no launch authorization or site suitability is implied.")

elif page == "Combustion parameter lab":
    st.subheader("Droplet combustion parameter exploration")
    st.caption("Educational sensitivity explorer. This is not a validated kinetic mechanism or a substitute for PSI-117 experimental data.")
    c1,c2 = st.columns(2)
    with c1:
        d0 = st.slider("Initial droplet diameter, d₀ (mm)", 0.1, 5.0, 2.0, 0.1)
        pressure = st.slider("Ambient pressure (atm)", 0.5, 5.0, 1.0, 0.25)
    with c2:
        oxygen = st.slider("Oxygen concentration, Xₒ₂ (%)", 10, 35, 21, 1)
        temp = st.slider("Initial ambient temperature (K)", 250, 450, 300, 5)
    # Retained only as a clearly-labelled heuristic from the submitted prototype.
    heuristic = d0 * 1.414 * np.sqrt(pressure) * (oxygen/21.0)
    st.metric("Prototype heuristic output", f"{heuristic:.3f} (unvalidated units)")
    st.warning("This preserves the original prototype's formula for comparison only. It is not called a burning-rate constant (K), and no physical unit is assigned until the equation is validated.")
    st.markdown("### One-factor sensitivity")
    d_values = np.linspace(0.1,5.0,50)
    curve = pd.DataFrame({"Droplet diameter (mm)":d_values,
                          "Prototype output":d_values*1.414*np.sqrt(pressure)*(oxygen/21.0)})
    st.plotly_chart(px.line(curve,x="Droplet diameter (mm)",y="Prototype output"),use_container_width=True)
    st.markdown("### Research variables to connect when source data is available")
    st.write("Ignition delay · flame stand-off diameter · extinction diameter · oscillation frequency · droplet diameter · temperature · pressure · time")

elif page == "Combustion theory & safety":
    st.subheader("Combustion theory & aerospace fire safety")
    st.markdown("""
    ### Cool flames and microgravity
    Cool-flame chemistry involves low-temperature oxidation pathways and can exhibit behaviour that differs from conventional hot flames. In microgravity, buoyancy-driven convection is strongly reduced, changing flame shape, transport and extinction behaviour.

    ### Why FLEX / PSI data matters
    NASA's Physical Sciences Informatics repository hosts investigations and datasets used to study physical phenomena in spaceflight environments. PSI-117 is listed as a ground investigation concerning external thermo-convective perturbations and cool-flame dynamics, using FLEX-related data and multiphysics modelling.

    ### Keep the evidence chain clear
    - Experimental observations should be labelled as measured data.
    - Model outputs should be labelled as simulated or inferred.
    - Assumptions, units, uncertainty and source files should be recorded.
    - A rocket's propulsion system and a droplet-combustion experiment are different physical systems. Do not transfer fuel properties or correlations between them without a defensible model.
    """)
    st.markdown(f"[NASA PSI repository]({PSI_URL}) · [NASA overview of microgravity combustion research](https://science.nasa.gov/physical-sciences-informatics-psi/)")

st.divider()
st.caption("AEROGUARD SIM · Research & Learning Platform · NASA PSI context · SLS vehicle reference. Educational prototype; not flight software, certification evidence or an operational safety system.")
