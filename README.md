# 🚀 AeroGuard Sim

**Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data**

> NASA Space Apps Hackathon 2026

## Overview

AeroGuard Sim is an interactive research & learning platform that combines:

- **🌍 3D Mission Simulator** — Launch NASA rockets from any point on a live CesiumJS globe with satellite imagery, gravity-turn animation, and real-time fire hazard visualization
- **🔥 ACME Combustion Lab** — Microgravity flame data with filters, scatter plots, and hazard correlation
- **📁 PSI-117 Dataset Explorer** — DOI-traceable droplet combustion benchmarks (n-heptane, n-dodecane, n-decane)
- **🎓 Student Learning Lab** — Interactive sliders for droplet diameter, pressure, and O₂ with closest ACME reference
- **🔒 Data Provenance Audit** — SHA-256 verified file uploads with audit trail

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit + Plotly + PyDeck |
| 3D Globe | CesiumJS 1.120 + NASA GIBS (MODIS Terra) + ArcGIS World Imagery |
| Data | NASA PSI-117, NASA ACME, FLEX-ISS |
| Physics | Simplified gravity-turn, d²-law burn rate, O₂ threshold hazard model |

## Folder Structure
   
