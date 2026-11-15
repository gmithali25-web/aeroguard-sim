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


# ============================================================
# AEROGUARD | PSI-117 DATA WORKSPACE
# This app does not generate NASA measurements. It only analyzes
# user-provided numerical files and clearly labels metadata files.
# ============================================================

st.set_page_config(
    page_title="AeroGuard | PSI-117 Research Workspace",
    page_icon="🛰️",
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
STUDY_TITLE = (
    "Effect of External Thermo-Convective Perturbation on Cool Flame Dynamics"
)
DOI = "10.60555/gz0q-b577"

# Candidate names are hints only. The app never creates missing values.
VARIABLE_HINTS = {
    "Ignition delay": [
        "ignition_delay", "ignition delay", "ignition_delay_s",
        "ignition delay (s)", "tau_ign", "tau_ignition",
    ],
    "Flame stand-off diameter": [
        "stand_off_diameter", "standoff_diameter", "flame_stand_off_diameter",
        "flame stand-off diameter", "stand off diameter",
    ],
    "Extinction diameter": [
        "extinction_diameter", "extinction diameter", "d_ext",
    ],
    "Oscillation frequency": [
        "oscillation_frequency", "frequency", "oscillation frequency",
        "frequency_hz",
    ],
    "Oscillation amplitude": [
        "oscillation_amplitude", "amplitude", "oscillation amplitude",
    ],
    "Droplet diameter": [
        "droplet_diameter", "initial_diameter", "initial_droplet_diameter",
        "droplet diameter",
    ],
    "Temperature": [
        "temperature", "temperature_k", "temp_k", "ambient_temperature",
        "ambient_t_k",
    ],
    "Pressure": [
        "pressure", "pressure_pa", "pressure_kpa",
    ],
    "Time": ["time", "time_s", "timestamp", "elapsed_time"],
    "External heat flux": [
        "heat_flux", "external_heat_flux", "imposed_heat_flux",
    ],
    "Convection / flow condition": [
        "convection", "flow_rate", "velocity", "external_flow",
    ],
}


# --------------------------- HELPERS -------------------------

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def read_csv_bytes(data: bytes) -> pd.DataFrame:
    """Read a CSV without changing the source values."""
    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(data), encoding=encoding)
        except Exception as exc:
            last_error = exc
    raise ValueError(f"Could not read CSV: {last_error}")


def read_uploaded_file(filename: str, data: bytes):
    """Return (numeric dataframe or None, text content or None, status)."""
    suffix = PurePosixPath(filename).suffix.lower()

    if suffix == ".csv":
        return read_csv_bytes(data), None, "Numerical table"

    if suffix in (".txt", ".md", ".json", ".xml"):
        text_value = data.decode("utf-8", errors="replace")
        return None, text_value, "Text / metadata document"

    if suffix in (".xlsx", ".xls"):
        try:
            frame = pd.read_excel(io.BytesIO(data))
            return frame, None, "Spreadsheet table"
        except ImportError:
            return None, None, "Spreadsheet not read: install openpyxl"
        except Exception as exc:
            return None, None, f"Spreadsheet read error: {exc}"

    return None, None, "Unsupported file type"


def inspect_upload(uploaded_file):
    """Inspect a single uploaded file, including CSV/TXT files inside ZIP."""
    filename = uploaded_file.name
    raw = uploaded_file.getvalue()
    file_records = []
    dataframes = []
    text_documents = []

    file_records.append({
        "File": filename,
        "Bytes": len(raw),
        "SHA-256": sha256_bytes(raw),
        "Uploaded UTC": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })

    if filename.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                for member in archive.infolist():
                    if member.is_dir():
                        continue
                    inner_name = member.filename
                    inner_suffix = PurePosixPath(inner_name).suffix.lower()
                    if inner_suffix not in (".csv", ".txt", ".md", ".json", ".xml", ".xlsx", ".xls"):
                        continue
                    content = archive.read(member)
                    file_records.append({
                        "File": f"{filename} :: {inner_name}",
                        "Bytes": len(content),
                        "SHA-256": sha256_bytes(content),
                        "Uploaded UTC": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    })
                    frame, text_value, status = read_uploaded_file(inner_name, content)
                    if frame is not None:
                        dataframes.append((f"{filename} :: {inner_name}", frame, sha256_bytes(content)))
                    if text_value is not None:
                        text_documents.append((f"{filename} :: {inner_name}", text_value))
                    if frame is None and text_value is None:
                        text_documents.append((f"{filename} :: {inner_name}", status))
        except zipfile.BadZipFile:
            text_documents.append((filename, "This file has a .zip extension but is not a valid ZIP archive."))
    else:
        frame, text_value, status = read_uploaded_file(filename, raw)
        if frame is not None:
            dataframes.append((filename, frame, sha256_bytes(raw)))
        if text_value is not None:
            text_documents.append((filename, text_value))
        if frame is None and text_value is None:
            text_documents.append((filename, status))

    return file_records, dataframes, text_documents


def guess_column(columns, hint_names):
    normalized = {normalize_name(c): c for c in columns}
    for hint in hint_names:
        key = normalize_name(hint)
        if key in normalized:
            return normalized[key]
    # Fuzzy matching on normalized tokens, still only a suggestion.
    for key, original in normalized.items():
        if any(normalize_name(h) in key or key in normalize_name(h) for h in hint_names):
            return original
    return None


def build_column_audit(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in df.columns:
        series = df[col]
        numeric = pd.to_numeric(series, errors="coerce")
        numeric_count = int(numeric.notna().sum())
        rows.append({
            "Column": str(col),
            "Detected type": str(series.dtype),
            "Rows with values": int(series.notna().sum()),
            "Missing values": int(series.isna().sum()),
            "Numeric values detected": numeric_count,
            "Unique values": int(series.nunique(dropna=True)),
        })
    return pd.DataFrame(rows)


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


# ---------------------------- HEADER -------------------------

with st.sidebar:
    st.markdown(
        '<div style="padding:8px 2px 18px"><div class="ag-brand">✧ AERO<span>GUARD</span></div>'
        '<div class="ag-sub">NASA PSI RESEARCH WORKSPACE</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<span class="ag-chip">DATA PROVENANCE FIRST</span>', unsafe_allow_html=True)
    page = st.radio(
        "NAVIGATION",
        [
            "Mission Overview",
            "Upload & Inspect Data",
            "Variable Explorer",
            "Data Quality & Log",
            "Study Metadata",
        ],
    )
    st.markdown("---")
    st.caption("ACTIVE STUDY")
    st.markdown(f"**{STUDY_ID}**")
    st.caption("Cool-flame dynamics")
    st.markdown("---")
    st.caption("DATA INTEGRITY")
    st.caption("No built-in synthetic NASA records. Only uploaded numerical data are analyzed.")

now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
st.markdown(
    f"""
    <div class="ag-top">
      <div>
        <div class="ag-brand">AEROGUARD <span>RESEARCH CONTROL</span></div>
        <div class="ag-sub">FLAME IN FREEFALL · PSI-117 DATA WORKSPACE</div>
      </div>
      <div style="text-align:right">
        <div style="color:#2ee6bd;font-family:'Space Mono';font-size:.72rem">● WORKSPACE READY</div>
        <div style="font-family:'Space Mono';font-size:.7rem;color:#8ba7c2">{now}</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------------- SESSION STATE -----------------------

if "datasets" not in st.session_state:
    st.session_state.datasets = []
if "file_log" not in st.session_state:
    st.session_state.file_log = []
if "text_documents" not in st.session_state:
    st.session_state.text_documents = []


# ----------------------- MISSION OVERVIEW --------------------

if page == "Mission Overview":
    st.title("PSI-117 Research Operations")
    st.caption("A transparent workspace for inspecting uploaded cool-flame research data.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi("STUDY ID", STUDY_ID, "NASA PSI investigation metadata")
    with c2:
        render_kpi("NUMERICAL DATASETS", str(len(st.session_state.datasets)), "Loaded in this session")
    with c3:
        total_rows = sum(len(item["data"]) for item in st.session_state.datasets)
        render_kpi("NUMERICAL ROWS", f"{total_rows:,}", "From uploaded files only")
    with c4:
        render_kpi("SOURCE FILES", str(len(st.session_state.file_log)), "Files inspected and logged")

    st.markdown('<div class="ag-panel">', unsafe_allow_html=True)
    st.markdown('<div class="ag-panel-title">CURRENT DATA STATUS</div>', unsafe_allow_html=True)
    if st.session_state.datasets:
        st.success("At least one numerical table has been uploaded. Open Variable Explorer to inspect its actual columns.")
    else:
        st.warning(
            "No numerical measurements are loaded. The PSI-117 metadata ZIP by itself does not provide "
            "a numerical measurement table for plotting or statistical analysis."
        )
    st.markdown(
        """
        **What this application does**
        - Reads uploaded CSV files and CSV/text/spreadsheet files contained in ZIP archives.
        - Displays original columns and values without inventing missing measurements.
        - Records file names, sizes, SHA-256 hashes, upload times and row/column information.
        - Lets you select variables and plot only values that actually exist in the uploaded table.
        - Exports the inspected data and a provenance log.

        **What it does not claim**
        - It does not connect live to NASA PSI.
        - It does not reconstruct missing PSI-117 simulation outputs from metadata.
        - It does not treat generated examples or guessed units as NASA measurements.
        """
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.info(
        "Start with **Upload & Inspect Data**. Upload the PSI-117 ZIP and, if you have them, "
        "the numerical CSV or spreadsheet files supplied separately."
    )


# ----------------------- UPLOAD & INSPECT --------------------

elif page == "Upload & Inspect Data":
    st.title("Upload & Inspect Research Files")
    st.caption("Upload the PSI-117 metadata package and any separate numerical result files.")

    uploaded_files = st.file_uploader(
        "Choose ZIP, CSV, TXT, JSON, XML or Excel files",
        type=["zip", "csv", "txt", "md", "json", "xml", "xlsx", "xls"],
        accept_multiple_files=True,
        help="ZIP archives are inspected for supported files inside them.",
    )

    if st.button("Process uploaded files", type="primary", disabled=not uploaded_files):
        new_datasets = []
        new_logs = []
        new_texts = []
        errors = []

        for uploaded in uploaded_files:
            try:
                logs, frames, texts = inspect_upload(uploaded)
                new_logs.extend(logs)
                new_texts.extend(texts)
                for source_name, frame, digest in frames:
                    if frame.empty:
                        errors.append(f"{source_name}: table is empty.")
                        continue
                    frame = frame.copy()
                    new_datasets.append({
                        "source": source_name,
                        "sha256": digest,
                        "data": frame,
                    })
            except Exception as exc:
                errors.append(f"{uploaded.name}: {exc}")

        st.session_state.datasets.extend(new_datasets)
        st.session_state.file_log.extend(new_logs)
        st.session_state.text_documents.extend(new_texts)

        if new_datasets:
            st.success(f"Loaded {len(new_datasets)} numerical table(s).")
        if new_texts:
            st.info(f"Found {len(new_texts)} text or metadata document(s).")
        for error in errors:
            st.error(error)

    if st.session_state.datasets:
        st.subheader("Loaded numerical tables")
        summary = []
        for i, item in enumerate(st.session_state.datasets):
            summary.append({
                "Dataset #": i + 1,
                "Source file": item["source"],
                "Rows": len(item["data"]),
                "Columns": len(item["data"].columns),
                "Column names": ", ".join(map(str, item["data"].columns)),
                "SHA-256": item["sha256"],
            })
        st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)

    if st.session_state.text_documents:
        st.subheader("Text and metadata files")
        for name, content in st.session_state.text_documents:
            with st.expander(name):
                st.text(str(content)[:20000])

    if st.button("Clear session data"):
        st.session_state.datasets = []
        st.session_state.file_log = []
        st.session_state.text_documents = []
        st.rerun()


# ----------------------- VARIABLE EXPLORER -------------------

elif page == "Variable Explorer":
    st.title("Measured Variable Explorer")
    st.caption("Choose columns from an uploaded numerical table. Candidate variable names are suggestions, not assumed facts.")

    if not st.session_state.datasets:
        st.warning("Upload a numerical CSV or spreadsheet first. Metadata text alone cannot produce measurement plots.")
    else:
        labels = [
            f"{i + 1}. {item['source']} ({len(item['data'])} rows)"
            for i, item in enumerate(st.session_state.datasets)
        ]
        selected = st.selectbox("Select numerical dataset", range(len(labels)), format_func=lambda x: labels[x])
        item = st.session_state.datasets[selected]
        df = item["data"]
        st.markdown(f'<span class="ag-chip">SOURCE: {item["source"]}</span>', unsafe_allow_html=True)

        st.subheader("Original data preview")
        st.dataframe(df.head(100), use_container_width=True, hide_index=True)

        st.subheader("Choose variables to plot")
        numeric_columns = [
            c for c in df.columns
            if pd.to_numeric(df[c], errors="coerce").notna().sum() > 0
        ]

        if not numeric_columns:
            st.warning("No numeric columns were detected in this table.")
        else:
            all_columns = list(df.columns)
            x_guess = guess_column(all_columns, VARIABLE_HINTS["Time"])
            if x_guess not in numeric_columns:
                x_guess = numeric_columns[0]

            x_col = st.selectbox("X-axis column", numeric_columns, index=numeric_columns.index(x_guess))
            y_options = [c for c in numeric_columns if c != x_col]
            if y_options:
                y_col = st.selectbox("Y-axis column", y_options, index=0)
                plot_df = df[[x_col, y_col]].copy()
                plot_df[x_col] = pd.to_numeric(plot_df[x_col], errors="coerce")
                plot_df[y_col] = pd.to_numeric(plot_df[y_col], errors="coerce")
                plot_df = plot_df.dropna()

                if len(plot_df) >= 2:
                    fig = px.scatter(
                        plot_df,
                        x=x_col,
                        y=y_col,
                        title=f"{y_col} vs {x_col}",
                        trendline=None,
                    )
                    fig.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        height=420,
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption(
                        f"Chart uses {len(plot_df)} rows from the selected uploaded file. "
                        "No missing measurements have been filled in."
                    )
                else:
                    st.warning("There are fewer than two complete numeric pairs for this selection.")

        st.subheader("Suggested PSI-117 variable mapping")
        mapping_rows = []
        for concept, hints in VARIABLE_HINTS.items():
            found = guess_column(df.columns, hints)
            mapping_rows.append({
                "Research concept": concept,
                "Possible matching source column": str(found) if found is not None else "Not found",
                "Status": "Candidate match — verify units" if found is not None else "Not present / not recognized",
            })
        st.dataframe(pd.DataFrame(mapping_rows), use_container_width=True, hide_index=True)
        st.caption(
            "A candidate name match is not proof that two fields have the same scientific definition. "
            "Check the source documentation and units before interpreting results."
        )

        st.download_button(
            "Download selected dataset as CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name="aeroguard_selected_uploaded_data.csv",
            mime="text/csv",
        )


# ----------------------- QUALITY & PROVENANCE LOG ------------

elif page == "Data Quality & Log":
    st.title("Data Quality & Provenance")
    st.caption("Audit what was uploaded and what values are present. This page does not certify scientific validity.")

    if st.session_state.file_log:
        log_df = pd.DataFrame(st.session_state.file_log)
        st.subheader("File-level provenance log")
        st.dataframe(log_df, use_container_width=True, hide_index=True)
        st.download_button(
            "Download provenance log",
            log_df.to_csv(index=False).encode("utf-8"),
            file_name="aeroguard_provenance_log.csv",
            mime="text/csv",
        )
    else:
        st.info("No files have been processed in this session yet.")

    if st.session_state.datasets:
        labels = [
            f"{i + 1}. {item['source']}"
            for i, item in enumerate(st.session_state.datasets)
        ]
        selected = st.selectbox("Choose dataset for column audit", range(len(labels)), format_func=lambda x: labels[x])
        df = st.session_state.datasets[selected]["data"]
        audit = build_column_audit(df)

        st.subheader("Column-level audit")
        st.dataframe(audit, use_container_width=True, hide_index=True)

        st.metric("Rows", f"{len(df):,}")
        st.metric("Columns", len(df.columns))
        st.metric("Duplicate rows", int(df.duplicated().sum()))

        st.download_button(
            "Download column audit",
            audit.to_csv(index=False).encode("utf-8"),
            file_name="aeroguard_column_audit.csv",
            mime="text/csv",
        )
    else:
        st.warning("Upload a numerical table to run a column-level audit.")


# ----------------------- STUDY METADATA ----------------------

elif page == "Study Metadata":
    st.title("PSI-117 Study Reference")
    st.caption("Study identity and research context recorded for this AeroGuard workspace.")

    st.markdown('<div class="ag-panel">', unsafe_allow_html=True)
    st.markdown(f"### {STUDY_ID} — {STUDY_TITLE}")
    st.write("**DOI:**", DOI)
    st.write("**Research domain:**", "Cool-flame dynamics and droplet combustion")
    st.write("**Modelling approach described in the supplied metadata:**",
             "3-D OpenFOAM CFD, low-temperature chemistry, heat and mass transfer, and radiation.")
    st.write("**Perturbation themes described:**",
             "External convection, imposed heating, and combined thermo-convective effects.")
    st.write("**Outputs / observables identified in the study description:**",
             "Ignition delay, oscillation frequency and amplitude, flame stand-off diameter, and extinction diameter.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.warning(
        "The supplied PSI-117 ZIP is a metadata package, not a numerical results table. "
        "This page records study context; it does not imply that the measurements are loaded."
    )
    st.markdown("### Research data interpretation checklist")
    st.markdown(
        """
        - Confirm the exact variable definition in the original source.
        - Confirm the unit for every numeric column.
        - Distinguish simulation outputs from experimental measurements.
        - Record the forcing condition and case identifier for each result.
        - Do not compare values from different conditions without documenting the difference.
        - Keep original files unchanged and retain their provenance hashes.
        """
    )

# ---------------------------- FOOTER -------------------------

st.markdown(
    """
    <div style="border-top:1px solid #173653;margin-top:22px;padding-top:12px;
                color:#7895af;font-size:.68rem">
      AEROGUARD · PSI-117 RESEARCH PROTOTYPE · UPLOADED DATA ONLY ·
      NO LIVE NASA CONNECTION · SCIENTIFIC INTERPRETATION REQUIRES SOURCE AND UNIT VALIDATION
    </div>
    """,
    unsafe_allow_html=True,
)
