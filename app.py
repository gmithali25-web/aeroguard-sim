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
import plotly.graph_objects as go
import streamlit as st
import pydeck as pdk


# ============================================================
# AEROGUARD SIM | RESEARCH & LEARNING AEROSPACE PLATFORM
# Tailored for Aerospace Research Scholars, Professors, and Students.
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
    .ag-panel-title {color:#dcecff; font-size:.91rem; font-weight:700; margin-bottom:8px;}
    .ag-muted {color:#8ba7c2; font-size:.78rem;}
    .ag-kpi {background:linear-gradient(145
