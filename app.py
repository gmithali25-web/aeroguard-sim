from __future__ import annotations
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="AeroGuard | Research Mission Control", page_icon="🛰️",
                   layout="wide", initial_sidebar_state="expanded")

# ---------- THEME ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap');
:root { --bg:#050d1b; --panel:#09182b; --panel2:#0b2038; --line:#173653;
        --cyan:#22d3ee; --teal:#19d3b0; --muted:#8ba7c2; --white:#eaf4ff; }
.stApp { background:radial-gradient(ellipse at 50% 0%, #0a1c33 0%, #050d1b 58%); color:var(--white); }
html, body, [class*="css"] { font-family:Inter,sans-serif; }
section[data-testid="stSidebar"] { background:#061326; border-right:1px solid #173653; }
section[data-testid="stSidebar"] * { color:#d8e8f7; }
.block-container { padding-top:1.1rem; padding-bottom:2rem; max-width:1800px; }
h1,h2,h3 { letter-spacing:-.035em; }
.ag-top { display:flex; justify-content:space-between; align-items:center; padding:8px 2px 15px;
          border-bottom:1px solid #173653; margin-bottom:16px; }
.ag-brand { font-size:1.22rem; font-weight:800; letter-spacing:.12em; color:#f1f8ff; }
.ag-brand span { color:#22d3ee; }
.ag-sub { font-size:.66rem; letter-spacing:.22em; color:#7796b3; }
.ag-online { color:#2ee6bd; font-family:'Space Mono'; font-size:.72rem; }
.ag-panel { background:linear-gradient(145deg,rgba(12,32,55,.97),rgba(6,19,36,.98));
            border:1px solid #173653; border-radius:13px; padding:14px 16px;
            box-shadow:0 8px 28px rgba(0,0,0,.18); margin-bottom:12px; }
.ag-panel-title { color:#dcecff; font-size:.91rem; font-weight:700; margin-bottom:8px; }
.ag-muted { color:#8ba7c2; font-size:.76rem; }
.ag-kpi { background:linear-gradient(145deg,#0c2340,#08172a); border:1px solid #1b4263;
          border-radius:11px; padding:12px 14px; min-height:92px; }
.ag-kpi-label { color:#8ba7c2; font-size:.68rem; letter-spacing:.1em; text-transform:uppercase; }
.ag-kpi-value { color:#f1f8ff; font-family:'Space Mono'; font-size:1.35rem; font-weight:700; margin-top:5px; }
.ag-kpi-foot { color:#25d8c0; font-size:.68rem; margin-top:3px; }
.ag-chip { display:inline-block; border:1px solid #176b70; background:#073b40; color:#67f3df;
           border-radius:20px; padding:3px 9px; font-size:.65rem; font-weight:700; letter-spacing:.06em; }
.ag-rule { border-top:1px solid #173653; margin:10px 0; }
div[data-testid="stMetric"] { background:#0b2038; border:1px solid #173653; padding:10px 12px; border-radius:10px; }
div[data-testid="stMetricLabel"] { color:#8ba7c2; }
div[data-testid="stMetricValue"] { color:#f1f8ff; font-family:'Space Mono'; }
.stButton>button, .stDownloadButton>button { background:#073b50; border:1px solid #167d96; color:#dffaff;
  border-radius:8px; font-weight:600; }
.stButton>button:hover, .stDownloadButton>button:hover { border-color:#22d3ee; color:white; }
div[data-testid="stDataFrame"] { border:1px solid #173653; border-radius:8px; }
.stTabs [data-baseweb="tab-list"] { gap:8px; }
.stTabs [data-baseweb="tab"] { background:#09182b; border:1px solid #173653; border-radius:8px 8px 0 0; }
.stTabs [aria-selected="true"] { color:#22d3ee !important; }
label, .stMarkdown p { color:#d5e6f5; }
footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ---------- HELPERS ----------
def panel_title(title, right=""):
    st.markdown(f'<div class="ag-panel-title">{title} <span style="float:right;color:#22d3ee;font-size:.68rem">{right}</span></div>', unsafe_allow_html=True)

def kpi(label, value, foot=""):
    st.markdown(f'<div class="ag-kpi"><div class="ag-kpi-label">{label}</div><div class="ag-kpi-value">{value}</div><div class="ag-kpi-foot">{foot}</div></div>', unsafe_allow_html=True)

def dark_fig(fig, height=270):
    fig.update_layout(template="plotly_dark", height=height, margin=dict(l=8,r=8,t=28,b=8),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter",color="#c9dced",size=11),
                      legend=dict(orientation="h",y=1.12,x=0),
                      xaxis=dict(gridcolor="#173653",zerolinecolor="#173653"),
                      yaxis=dict(gridcolor="#173653",zerolinecolor="#173653"))
    return fig

def isa_atmosphere(alt_m):
    """Simplified layered US Standard Atmosphere calculation, geopotential altitude."""
    h = float(np.clip(alt_m, 0, 27432))
    layers = [(0,288.15,-0.0065),(11000,216.65,0.0),(20000,216.65,0.001)]
    g0, R = 9.80665, 287.05287
    base_p = [101325.0]
    for i in range(1, len(layers)):
        hb, tb, lapse = layers[i-1]
        hn, tn, _ = layers[i]
        if abs(lapse) < 1e-12:
            p = base_p[-1]*math.exp(-g0*(hn-hb)/(R*tb))
        else:
            p = base_p[-1]*(tn/tb)**(-g0/(lapse*R))
        base_p.append(p)
    if h < 11000:
        hb,tb,L=layers[0]; p=base_p[0]*(1+L*(h-hb)/tb)**(-g0/(L*R)); T=tb+L*h
    elif h < 20000:
        hb,tb,L=layers[1]; p=base_p[1]*math.exp(-g0*(h-hb)/(R*tb)); T=tb
    else:
        hb,tb,L=layers[2]; T=tb+L*(h-hb); p=base_p[2]*(T/tb)**(-g0/(L*R))
    rho=p/(R*T); a=math.sqrt(1.4*R*T)
    return T, p, rho, a

def demo_combustion():
    rng=np.random.default_rng(17)
    n=48
    return pd.DataFrame({
        "Experiment_ID":[f"DEMO-{i:03d}" for i in range(1,n+1)],
        "Fuel":[["Heptane droplet","Methane","PMMA","Ethanol"][i%4] for i in range(n)],
        "Oxygen_pct":rng.uniform(15,30,n).round(2),
        "Ambient_T_K":rng.uniform(285,305,n).round(2),
        "Pressure_kPa":rng.uniform(90,103,n).round(2),
        "Initial_diameter_mm":rng.uniform(0.8,2.4,n).round(3),
        "Flame_duration_s":rng.uniform(1.2,18,n).round(2),
        "Outcome":rng.choice(["Sustained","Extinguished"],n,p=[.62,.38])
    })

# ---------- SIDEBAR ----------
with st.sidebar:
    st.markdown('<div style="padding:8px 2px 18px"><div class="ag-brand">✧ AERO<span>GUARD</span></div><div class="ag-sub">AEROSPACE RESEARCH SYSTEMS</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="ag-chip">● RESEARCH WORKSPACE ONLINE</div>', unsafe_allow_html=True)
    page = st.radio("NAVIGATION", ["Mission Dashboard","Combustion Explorer","Swarm Intelligence Lab",
        "Fire Safety Insights","Ascent Environment","Aerothermal Analysis","Research Library"],
        label_visibility="visible")
    st.markdown("---")
    st.caption("ACTIVE WORKSPACE")
    st.markdown("**Microgravity Combustion**")
    st.caption("Secondary system · SLS ascent environment")
    st.markdown("---")
    st.caption("DATA INTEGRITY")
    st.caption("Demo records are labelled. NASA measurements are not fabricated or implied.")

# ---------- TOP HEADER ----------
now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"""
<div class="ag-top">
 <div><div class="ag-brand">AEROGUARD <span>MISSION CONTROL</span></div>
 <div class="ag-sub">FLAME IN FREEFALL · SI-POWERED COMBUSTION RESEARCH</div></div>
 <div style="text-align:right"><div class="ag-online">● SYSTEM ONLINE</div>
 <div style="font-family:'Space Mono';font-size:.7rem;color:#8ba7c2">UTC {now}</div></div>
</div>""", unsafe_allow_html=True)

# ---------- DASHBOARD ----------
if page == "Mission Dashboard":
    st.markdown("## Research Operations Overview")
    st.caption("A unified workspace for microgravity combustion research and aerospace environment exploration.")
    c1,c2,c3,c4=st.columns(4)
    with c1: kpi("PRIMARY INVESTIGATION","FLEX","NASA microgravity combustion")
    with c2: kpi("ANALYSIS ENGINE","PSO / SI","Optimization workspace")
    with c3: kpi("ASCENT ENVELOPE","0–90 kft","Atmospheric model")
    with c4: kpi("REFERENCE VEHICLE","SLS BLOCK 1","Published configuration reference")
    left, right = st.columns([1.65,1])
    with left:
        st.markdown('<div class="ag-panel">',unsafe_allow_html=True)
        panel_title("COMBUSTION RESEARCH VISUALIZATION","MICROGRAVITY")
        # Original conceptual flame visualization, not an experimental photograph.
        theta=np.linspace(0,2*np.pi,220)
        r=1.0+0.12*np.sin(5*theta)+0.05*np.cos(9*theta)
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=r*np.cos(theta),y=r*np.sin(theta),mode="lines",
            line=dict(color="#22d3ee",width=3),fill="toself",fillcolor="rgba(34,211,238,.12)",name="Conceptual flame boundary"))
        rng=np.random.default_rng(4)
        x=rng.normal(0,.42,220); y=rng.normal(0,.42,220)
        fig.add_trace(go.Scatter(x=x,y=y,mode="markers",marker=dict(size=2,color="#ff9b54",opacity=.55),name="Illustrative particles"))
        fig.update_layout(xaxis=dict(visible=False,scaleanchor="y",range=[-1.6,1.6]),
                          yaxis=dict(visible=False,range=[-1.6,1.6]),showlegend=False)
        dark_fig(fig,390)
        st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
        st.caption("Conceptual visualization only — not a NASA flame image or measured flame geometry.")
        st.markdown('</div>',unsafe_allow_html=True)
    with right:
        st.markdown('<div class="ag-panel">',unsafe_allow_html=True)
        panel_title("RESEARCH SYSTEM STATUS")
        for name,status,clr in [("Dataset connector","AWAITING VERIFIED DATA","#e9b44c"),
                                ("Combustion analytics","READY FOR DATA","#22d3ee"),
                                ("Swarm optimizer","PROTOTYPE","#22d3ee"),
                                ("Ascent atmosphere model","AVAILABLE","#19d3b0"),
                                ("NASA source registry","REFERENCE MODE","#e9b44c")]:
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #173653"><span style="font-size:.8rem">{name}</span><span style="font-size:.65rem;color:{clr};font-weight:700">{status}</span></div>',unsafe_allow_html=True)
        st.markdown('<div class="ag-rule"></div><div class="ag-muted">No live spacecraft connection. No live NASA telemetry. Research and simulation workspace.</div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)
    b1,b2,b3=st.columns([1.15,1.15,1])
    with b1:
        st.markdown('<div class="ag-panel">',unsafe_allow_html=True); panel_title("RESEARCH PIPELINE")
        st.markdown("**01**  Dataset verification  <span style='color:#e9b44c'>PENDING</span><br>**02**  Feature extraction  <span style='color:#22d3ee'>READY</span><br>**03**  SI optimization  <span style='color:#22d3ee'>PROTOTYPE</span><br>**04**  Evidence review  <span style='color:#8ba7c2'>PLANNED</span>",unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)
    with b2:
        st.markdown('<div class="ag-panel">',unsafe_allow_html=True); panel_title("ASCENT ENVIRONMENT")
        alts=np.linspace(0,27432,50); vals=[isa_atmosphere(x) for x in alts]
        f=go.Figure(go.Scatter(x=alts/1000,y=[v[0]-273.15 for v in vals],mode="lines",line=dict(color="#22d3ee",width=2),name="Air temperature"))
        f.update_layout(xaxis_title="Altitude (km)",yaxis_title="Temperature (°C)")
        st.plotly_chart(dark_fig(f,190),use_container_width=True,config={"displayModeBar":False})
        st.markdown('</div>',unsafe_allow_html=True)
    with b3:
        st.markdown('<div class="ag-panel">',unsafe_allow_html=True); panel_title("REFERENCE VEHICLE")
        st.markdown("**NASA SLS · Block 1**<br><span class='ag-muted'>Human exploration launch vehicle</span><div class='ag-rule'></div><b>322 ft</b> <span class='ag-muted'>approx. height</span><br><b>8.8 million lbf</b> <span class='ag-muted'>approx. liftoff thrust</span><div class='ag-rule'></div><span class='ag-muted'>Reference specifications only. Not live flight telemetry.</span>",unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)

# ---------- COMBUSTION EXPLORER ----------
elif page == "Combustion Explorer":
    st.markdown("## Microgravity Combustion Explorer")
    st.caption("Inspect, filter and compare experimental records. Upload a verified NASA or mentor-provided dataset to replace the clearly labelled demonstration records.")
    uploaded=st.file_uploader("Upload combustion dataset (CSV)",type=["csv"])
    if uploaded:
        try: df=pd.read_csv(uploaded); source="USER-UPLOADED FILE"
        except Exception as e: st.error(f"Could not read CSV: {e}"); df=demo_combustion(); source="DEMO DATA"
    else: df=demo_combustion(); source="ILLUSTRATIVE DEMO DATA"
    st.markdown(f'<span class="ag-chip">{source}</span>',unsafe_allow_html=True)
    st.warning("The built-in rows are synthetic interface demonstration data. They are not NASA experimental measurements.")
    search=st.text_input("Search experiment ID, fuel or outcome")
    if search: df=df[df.astype(str).apply(lambda col: col.str.contains(search,case=False,na=False)).any(axis=1)]
    c1,c2,c3=st.columns(3)
    c1.metric("Records displayed",len(df))
    c2.metric("Fuel/material categories",df["Fuel"].nunique() if "Fuel" in df else "—")
    c3.metric("Columns",len(df.columns))
    st.dataframe(df,use_container_width=True,hide_index=True)
    if len(df) and "Oxygen_pct" in df and "Flame_duration_s" in df:
        f=px.scatter(df,x="Oxygen_pct",y="Flame_duration_s",color="Outcome" if "Outcome" in df else None,
                     hover_data=list(df.columns),title="Oxygen concentration vs flame duration")
        st.plotly_chart(dark_fig(f,340),use_container_width=True)
    st.download_button("Export displayed records",df.to_csv(index=False).encode(), "aeroguard_combustion_records.csv","text/csv")

# ---------- SWARM LAB ----------
elif page == "Swarm Intelligence Lab":
    st.markdown("## Swarm Intelligence Laboratory")
    st.caption("A transparent optimization workbench. The current demonstration objective is mathematical, not a validated combustion law.")
    st.info("Next research integration: define a fitness function against verified FLEX measurements or a validated combustion model, then test on held-out experiments.")
    c1,c2,c3=st.columns(3)
    with c1: n=st.slider("Particle count",10,100,30,5)
    with c2: iters=st.slider("Iterations",20,300,100,10)
    with c3: seed=st.number_input("Random seed",0,9999,42)
    if st.button("Run demonstration PSO",type="primary"):
        rng=np.random.default_rng(int(seed)); pos=rng.uniform(-5,5,(n,2)); vel=np.zeros_like(pos)
        pbest=pos.copy(); fit=lambda z: np.sum(z*z,axis=1)
        pscore=fit(pos); gbest=pbest[np.argmin(pscore)].copy(); history=[]
        for _ in range(iters):
            r1=rng.random((n,2)); r2=rng.random((n,2))
            vel=.72*vel+1.45*r1*(pbest-pos)+1.45*r2*(gbest-pos)
            pos=np.clip(pos+vel,-5,5); score=fit(pos)
            better=score<pscore; pbest[better]=pos[better]; pscore[better]=score[better]
            gbest=pbest[np.argmin(pscore)].copy(); history.append(float(np.min(pscore)))
        st.session_state["pso_history"]=history; st.session_state["pso_best"]=gbest
    if "pso_history" in st.session_state:
        st.metric("Best objective found",f"{st.session_state['pso_history'][-1]:.6f}")
        f=go.Figure(go.Scatter(y=st.session_state["pso_history"],mode="lines",line=dict(color="#22d3ee",width=3),name="Best objective"))
        f.update_layout(xaxis_title="Iteration",yaxis_title="Objective value")
        st.plotly_chart(dark_fig(f,330),use_container_width=True)
        st.write("Best point:",np.round(st.session_state["pso_best"],5))
        st.caption("This validates the optimizer mechanics on a simple mathematical test function only. It is not a combustion discovery.")
    else: st.markdown('<div class="ag-panel ag-muted">Run the optimizer to view convergence diagnostics.</div>',unsafe_allow_html=True)

# ---------- FIRE SAFETY ----------
elif page == "Fire Safety Insights":
    st.markdown("## Fire Safety Intelligence")
    st.caption("Evidence-linked interpretation layer — findings must be traceable to experimental records.")
    st.warning("No verified combustion dataset is connected yet. The examples below are research questions, not generated scientific conclusions.")
    items=[
        ("Flame persistence","Which measured conditions are associated with longer flame duration?","Requires duration labels and experimental conditions."),
        ("Extinction behaviour","Which combinations of oxygen and suppressant conditions are associated with extinction?","Requires suppressant composition and extinction outcomes."),
        ("Cool-flame observations","Are there post-visible-flame reactions documented in the selected experiment?","Requires experiment-specific diagnostics and source papers."),
        ("Material comparison","How do fuel/material classes differ under comparable conditions?","Requires comparable test conditions and uncertainty estimates.")]
    for title,q,need in items:
        with st.expander(title,expanded=True):
            st.write(q); st.caption("Evidence required: "+need)
    st.markdown("**Required insight record format**")
    st.dataframe(pd.DataFrame([
        {"Field":"Finding","Purpose":"One concise evidence-based statement"},
        {"Field":"Supporting experiments","Purpose":"Record identifiers and source links"},
        {"Field":"Method","Purpose":"Statistical test, model or SI method"},
        {"Field":"Uncertainty","Purpose":"Confidence interval or known limitations"},
        {"Field":"Safety relevance","Purpose":"Potential implication, not operational instruction"}]),use_container_width=True,hide_index=True)

# ---------- ASCENT ----------
elif page == "Ascent Environment":
    st.markdown("## Aerospace Ascent Environment Explorer")
    st.caption("Atmospheric reference calculator for 0–90,000 ft. This is not a complete SLS flight trajectory.")
    altitude_ft=st.slider("Select geopotential altitude",0,90000,40000,1000)
    T,P,rho,a=isa_atmosphere(altitude_ft*0.3048)
    c1,c2,c3,c4=st.columns(4)
    with c1: kpi("AIR TEMPERATURE",f"{T-273.15:.1f} °C",f"{T:.1f} K")
    with c2: kpi("PRESSURE",f"{P/1000:.2f} kPa",f"{P:.0f} Pa")
    with c3: kpi("AIR DENSITY",f"{rho:.4f} kg/m³","Standard atmosphere estimate")
    with c4: kpi("SPEED OF SOUND",f"{a:.1f} m/s","Local atmospheric value")
    alts=np.linspace(0,90000,181); rows=[isa_atmosphere(x*.3048) for x in alts]
    f=go.Figure()
    f.add_trace(go.Scatter(x=alts,y=[v[0]-273.15 for v in rows],name="Temperature (°C)",line=dict(color="#22d3ee",width=3)))
    f.update_layout(xaxis_title="Altitude (ft)",yaxis_title="Temperature (°C)",title="Standard-atmosphere temperature profile")
    st.plotly_chart(dark_fig(f,330),use_container_width=True)
    f2=go.Figure()
    f2.add_trace(go.Scatter(x=alts,y=[v[1]/1000 for v in rows],name="Pressure (kPa)",line=dict(color="#19d3b0",width=3)))
    f2.add_trace(go.Scatter(x=alts,y=[v[2] for v in rows],name="Density (kg/m³)",line=dict(color="#e9b44c",width=3),yaxis="y2"))
    f2.update_layout(title="Pressure and density vs altitude",xaxis_title="Altitude (ft)",yaxis=dict(title="Pressure (kPa)"),yaxis2=dict(title="Density (kg/m³)",overlaying="y",side="right"))
    st.plotly_chart(dark_fig(f2,300),use_container_width=True)
    st.caption("Model note: simplified layered standard-atmosphere calculation for educational exploration. It excludes weather, latitude/season variations and upper-atmosphere composition effects.")

# ---------- AEROTHERMAL ----------
elif page == "Aerothermal Analysis":
    st.markdown("## Vehicle Aerodynamics & Thermal Analysis")
    st.caption("Parameterized research calculator. Inputs are user-selected assumptions, not measured SLS flight telemetry.")
    c1,c2,c3=st.columns(3)
    with c1: alt=st.slider("Altitude (ft)",0,90000,40000,1000,key="thermal_alt")
    with c2: velocity=st.number_input("Vehicle speed (m/s)",min_value=0.0,max_value=8000.0,value=1200.0,step=50.0)
    with c3: cd=st.number_input("Drag coefficient Cd",min_value=0.05,max_value=2.0,value=0.5,step=0.05)
    area=st.number_input("Reference area (m²)",min_value=0.1,max_value=500.0,value=10.0)
    nose=st.number_input("Nose radius (m) for heating estimate",min_value=0.05,max_value=10.0,value=1.5)
    T,P,rho,a=isa_atmosphere(alt*.3048)
    q=.5*rho*velocity**2
    drag=q*cd*area
    mach=velocity/a
    k_sg=1.83e-4 # illustrative SI coefficient convention; validity must be checked for selected gas/model
    qdot=k_sg*math.sqrt(max(rho,0)/nose)*velocity**3
    m1,m2,m3,m4=st.columns(4)
    with m1: kpi("MACH NUMBER",f"{mach:.2f}","Speed / local sound speed")
    with m2: kpi("DYNAMIC PRESSURE",f"{q/1000:.2f} kPa","0.5 × density × relative speed²")
    with m3: kpi("ESTIMATED DRAG",f"{drag/1000:.1f} kN","Assumed Cd and area")
    with m4: kpi("HEATING INDICATOR",f"{qdot/1000:.2f} kW/m²","Correlation estimate; verify validity")
    st.warning("This simplified heating estimate is not an SLS-certified aerothermal prediction. The coefficient, gas model, geometry, flow regime and correlation validity must be verified before research use. Atmospheric temperature is not vehicle skin temperature.")
    st.markdown("**Calculation trace**")
    st.code(f"Altitude = {alt:,} ft\nAir density = {rho:.6f} kg/m³\nRelative speed assumed = {velocity:.1f} m/s\nDynamic pressure = 0.5 × {rho:.6f} × {velocity:.1f}² = {q:.2f} Pa\nDrag = q × Cd × area = {drag:.2f} N")
    st.caption("Wind is not yet included: enter air-relative velocity, not ground-relative velocity. A validated flight model must calculate relative airflow from wind and vehicle motion.")

# ---------- LIBRARY ----------
elif page == "Research Library":
    st.markdown("## Research Library & Provenance")
    st.caption("Register source documents and record which models support each calculation.")
    refs=pd.DataFrame([
        ["NASA Physical Sciences Informatics (PSI)","Dataset repository","Combustion investigation records","To be queried and verified"],
        ["FLEX investigation","Microgravity combustion","Flame extinction and suppressant research","Dataset availability to verify"],
        ["U.S. Standard Atmosphere 1976","Atmospheric reference","Temperature, pressure and density profiles","Reference model"],
        ["NASA SLS Block 1 reference guide","Vehicle specifications","Vehicle configuration and propulsion reference","Reference document"],
        ["NASA Artemis mission press kit","Mission milestones","Published ascent event timeline","Reference document"],
    ],columns=["Source","Type","AeroGuard use","Integration status"])
    st.dataframe(refs,use_container_width=True,hide_index=True)
    st.info("Before presenting numerical combustion findings, attach the exact source dataset and document version. Do not treat inherited sample rows as NASA data.")
    st.download_button("Download source register CSV",refs.to_csv(index=False).encode(),"aeroguard_source_register.csv","text/csv")

st.markdown('<div style="border-top:1px solid #173653;margin-top:22px;padding-top:12px;color:#7895af;font-size:.68rem">AEROGUARD V7.0 · RESEARCH PROTOTYPE · NO LIVE SPACECRAFT CONNECTION · SIMULATIONS REQUIRE VALIDATION BEFORE SCIENTIFIC OR OPERATIONAL USE</div>',unsafe_allow_html=True)
