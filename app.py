import time
import uuid
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AeroGuard Sim | Microgravity Fire Scenarios",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# STYLING
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0b1120;
        color: #e2e8f0;
    }

    div[data-testid="stMetric"] {
        background-color: #111c30;
        border: 1px solid #26354e;
        padding: 16px;
        border-radius: 12px;
    }

    .hero {
        background: linear-gradient(135deg, #111c30, #172c47);
        border: 1px solid #334155;
        padding: 28px;
        border-radius: 16px;
        margin-bottom: 20px;
    }

    .hero h1 {
        margin-bottom: 8px;
        color: #f8fafc;
    }

    .hero p {
        color: #cbd5e1;
        font-size: 17px;
        max-width: 850px;
    }

    .small-note {
        color: #94a3b8;
        font-size: 13px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DEMONSTRATION DATA
# These values are illustrative, not verified NASA measurements.
# ============================================================

@st.cache_data
def load_demo_materials():
    return pd.DataFrame(
        {
            "Material": [
                "Propane-like gas",
                "Acrylic-like polymer",
                "Wire-insulation-like polymer",
                "Fabric-like material",
                "Silicone-like polymer",
            ],
            "Category": [
                "Gas",
                "Thermoplastic",
                "Wiring insulation",
                "Fabric",
                "Polymer",
            ],
            "Reference_Spread": [3.2, 14.8, 1.9, 18.5, 13.4],
            "Reference_Oxygen": [18.0, 30.0, 24.5, 26.0, 32.0],
            "Reference_Airflow": [5.0, 10.2, 0.8, 12.0, 8.0],
            "Reference_Heat": [12.5, 45.0, 9.4, 38.5, 36.8],
        }
    )


materials = load_demo_materials()

HABITATS = [
    "Generic orbital laboratory",
    "Generic habitation module",
    "Generic logistics module",
    "Generic crew capsule",
]

PHASES = [
    "Orbital scenario",
    "Ascent scenario",
    "Ground demonstration",
]


# ============================================================
# SESSION STATE
# ============================================================

DEFAULTS = {
    "demo_open": False,
    "run": None,
    "history": [],
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# MODEL
# These are deliberately simplified demonstration relationships.
# No structural or operational safety predictions are made.
# ============================================================

def spread_proxy(material, oxygen, airflow, hvac_off, power_off):
    effective_flow = 0.2 if hvac_off else airflow

    flow_multiplier = (
        1.4
        if effective_flow < 2.0
        else 1.0 + effective_flow / 14.0
    )

    oxygen_multiplier = (oxygen / 21.0) ** 1.85

    value = (
        material["Reference_Spread"]
        * oxygen_multiplier
        * flow_multiplier
    )

    if power_off:
        value *= 0.35

    return float(value)


def current_spread(run):
    return spread_proxy(
        run["material"],
        run["oxygen"],
        run["airflow"],
        run["hvac_off"],
        run["power_off"],
    )


def add_event(run, message):
    elapsed = min(
        time.monotonic() - run["started_monotonic"],
        run["duration"],
    )

    run["events"].append(
        {
            "Elapsed_s": round(elapsed, 2),
            "Event": message,
        }
    )


def save_result(run):
    if run["saved"]:
        return

    st.session_state.history.append(
        {
            "Run_ID": run["id"],
            "Started_UTC": run["started_utc"],
            "Habitat": run["habitat"],
            "Phase_Label": run["phase"],
            "Material": run["material"]["Material"],
            "Oxygen_pct": run["oxygen"],
            "Airflow_cm_s": run["airflow"],
            "Planned_Duration_s": run["duration"],
            "Elapsed_s": round(run["elapsed"], 2),
            "Final_Demo_Score": round(run["score"], 2),
            "HVAC_Isolated": run["hvac_off"],
            "Power_Off": run["power_off"],
            "Outcome": run["outcome"],
        }
    )

    run["saved"] = True


def finish_run(run, outcome):
    if not run["active"]:
        return

    run["active"] = False
    run["outcome"] = outcome
    add_event(run, outcome)
    save_result(run)


def advance_run(run):
    if not run or not run["active"]:
        return

    now = time.monotonic()
    end_time = run["started_monotonic"] + run["duration"]
    update_until = min(now, end_time)

    dt = max(0.0, update_until - run["last_update"])

    if dt > 0:
        rate = current_spread(run)

        run["score"] = min(
            100.0,
            run["score"] + rate * 0.12 * dt,
        )

        run["elapsed"] = min(
            update_until - run["started_monotonic"],
            run["duration"],
        )

        run["last_update"] = update_until

        # Deterministic, synthetic signals—not sensor readings.
        elapsed = run["elapsed"]
        score = run["score"]

        run["telemetry"].append(
            {
                "Elapsed_s": round(elapsed, 2),
                "Synthetic_CO_ppm": round(
                    1.2 + score * 0.18, 2
                ),
                "Synthetic_Smoke_Index": round(
                    0.08 + score * 0.012, 3
                ),
                "Synthetic_Temperature_C": round(
                    22.4 + score * 0.16, 2
                ),
            }
        )

    if now >= end_time:
        finish_run(run, "Timed drill completed")


def create_run(habitat, phase, material, oxygen, airflow, duration):
    now = time.monotonic()

    run = {
        "id": str(uuid.uuid4())[:8],
        "started_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "started_monotonic": now,
        "last_update": now,
        "elapsed": 0.0,
        "duration": duration,
        "habitat": habitat,
        "phase": phase,
        "material": material.copy(),
        "oxygen": oxygen,
        "airflow": airflow,
        "score": 0.0,
        "hvac_off": False,
        "power_off": False,
        "active": True,
        "saved": False,
        "outcome": "Running",
        "events": [
            {
                "Elapsed_s": 0.0,
                "Event": "Drill started",
            }
        ],
        "telemetry": [
            {
                "Elapsed_s": 0.0,
                "Synthetic_CO_ppm": 1.2,
                "Synthetic_Smoke_Index": 0.08,
                "Synthetic_Temperature_C": 22.4,
            }
        ],
    }

    return run


# ============================================================
# INTRODUCTION
# ============================================================

if not st.session_state.demo_open:
    st.markdown(
        """
        <div class="hero">
            <h1>AeroGuard Sim</h1>
            <p>
                Explore microgravity fire scenarios through an
                interactive, simplified demonstration model.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([3, 2])

    with left:
        st.subheader("Configure. Run. Compare.")

        st.write(
            "Choose a material and atmosphere, run a timed drill, "
            "and explore the effects of simulated interventions."
        )

        st.markdown(
            """
            - Adjust oxygen and ventilation settings.
            - Follow synthetic telemetry during a drill.
            - Try simulated ventilation and power interventions.
            - Download results for your own analysis.
            """
        )

        if st.button(
            "Explore the simulator",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.demo_open = True
            st.rerun()

        st.caption("No account required.")

    with right:
        st.warning(
            "Educational prototype only. Material values, telemetry, "
            "and model relationships are illustrative. Not validated "
            "for spacecraft operations, fire suppression, structural "
            "assessment, or life-support decisions."
        )

    with st.expander("What this prototype does not do"):
        st.write(
            "It does not connect to real sensors, operate hardware, "
            "predict structural integrity, or recommend safe oxygen "
            "and ventilation settings. No NASA affiliation, approval, "
            "or dataset validation is claimed."
        )

    st.stop()


# ============================================================
# SIDEBAR CONFIGURATION
# ============================================================

st.sidebar.title("Scenario setup")
st.sidebar.caption("Guest demonstration")

habitat = st.sidebar.selectbox(
    "Habitat label",
    HABITATS,
)

phase = st.sidebar.selectbox(
    "Flight-phase label",
    PHASES,
)

st.sidebar.caption(
    "Habitat and phase are descriptive labels only. "
    "They do not change this model."
)

selected_material = st.sidebar.selectbox(
    "Demonstration material",
    materials["Material"].tolist(),
)

oxygen = st.sidebar.slider(
    "Oxygen concentration (%)",
    min_value=10.0,
    max_value=50.0,
    value=24.5,
    step=0.5,
)

airflow = st.sidebar.slider(
    "Ventilation setting (cm/s)",
    min_value=0.0,
    max_value=50.0,
    value=6.5,
    step=0.5,
)

duration = st.sidebar.selectbox(
    "Drill duration (seconds)",
    [10, 20, 30, 45, 60],
    index=1,
)

st.sidebar.info(
    "Settings are captured when a drill starts. "
    "Changing these controls does not alter an existing drill."
)

if st.sidebar.button(
    "Return to introduction",
    use_container_width=True,
):
    existing = st.session_state.run

    if existing and existing["active"]:
        advance_run(existing)
        finish_run(existing, "Stopped: returned to introduction")

    st.session_state.demo_open = False
    st.rerun()


# ============================================================
# MAIN HEADER
# ============================================================

st.title("AeroGuard Sim")
st.write(
    "A simplified fire-scenario explorer with synthetic telemetry."
)

st.warning(
    "Demonstration only—not a fire-safety prediction or control system."
)


# ============================================================
# AUTO-REFRESHING DASHBOARD
# ============================================================

@st.fragment(run_every="1s")
def render_dashboard():
    run = st.session_state.run
    advance_run(run)

    running = bool(run and run["active"])

    start_col, stop_col, clear_col = st.columns(3)

    with start_col:
        start_clicked = st.button(
            "Start new drill",
            type="primary",
            disabled=running,
            use_container_width=True,
        )

    with stop_col:
        stop_clicked = st.button(
            "Stop and save drill",
            disabled=not running,
            use_container_width=True,
        )

    with clear_col:
        clear_clicked = st.button(
            "Clear current view",
            disabled=running or run is None,
            use_container_width=True,
        )

    if start_clicked:
        material = materials.loc[
            materials["Material"] == selected_material
        ].iloc[0].to_dict()

        st.session_state.run = create_run(
            habitat=habitat,
            phase=phase,
            material=material,
            oxygen=oxygen,
            airflow=airflow,
            duration=duration,
        )

        st.rerun(scope="fragment")

    if stop_clicked:
        advance_run(run)
        finish_run(run, "Stopped by user")
        st.rerun(scope="fragment")

    if clear_clicked:
        st.session_state.run = None
        st.rerun(scope="fragment")

    if run is None:
        st.info(
            "Choose settings in the sidebar, then select "
            "'Start new drill'."
        )
    else:
        render_current_run(run)

    st.divider()
    render_history()


def render_current_run(run):
    remaining = max(0.0, run["duration"] - run["elapsed"])

    st.caption(
        f"Run {run['id']} | {run['habitat']} | "
        f"{run['material']['Material']} | "
        f"Oxygen: {run['oxygen']}% | "
        f"Ventilation: {run['airflow']} cm/s"
    )

    if run["active"]:
        st.info(
            f"Drill running — approximately {remaining:.0f} seconds left."
        )
    else:
        st.success(f"Drill ended: {run['outcome']}")

    k1, k2, k3, k4 = st.columns(4)

    k1.metric("Elapsed time", f"{run['elapsed']:.1f} s")
    k2.metric("Demo accumulation score", f"{run['score']:.1f} / 100")
    k3.metric("Spread proxy", f"{current_spread(run):.2f}")
    k4.metric(
        "Interventions applied",
        int(run["hvac_off"]) + int(run["power_off"]),
    )

    st.caption(
        "The score and spread proxy are illustrative model outputs. "
        "They are not measured damage, structural integrity, "
        "or validated flame-spread predictions."
    )

    st.progress(min(1.0, run["elapsed"] / run["duration"]))

    telemetry_tab, control_tab, events_tab, export_tab = st.tabs(
        [
            "Synthetic telemetry",
            "Simulated interventions",
            "Event timeline",
            "Export current drill",
        ]
    )

    with telemetry_tab:
        telemetry = pd.DataFrame(run["telemetry"])

        signal = st.selectbox(
            "Signal",
            [
                "Synthetic_CO_ppm",
                "Synthetic_Smoke_Index",
                "Synthetic_Temperature_C",
            ],
            key=f"signal_{run['id']}",
        )

        fig = go.Figure(
            go.Scatter(
                x=telemetry["Elapsed_s"],
                y=telemetry[signal],
                mode="lines+markers",
                name=signal.replace("_", " "),
                line={"color": "#38bdf8", "width": 3},
            )
        )

        fig.update_layout(
            template="plotly_dark",
            height=350,
            xaxis_title="Elapsed simulation time (seconds)",
            yaxis_title=signal.replace("_", " "),
            margin={"l": 15, "r": 15, "t": 25, "b": 15},
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption("All signals are generated by the demo model.")

    with control_tab:
        st.write(
            "These controls change simulation state only. "
            "They do not connect to real hardware."
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            if st.button(
                "Toggle ventilation isolation",
                disabled=not run["active"],
                use_container_width=True,
            ):
                advance_run(run)

                if run["active"]:
                    run["hvac_off"] = not run["hvac_off"]
                    add_event(
                        run,
                        "Ventilation isolated"
                        if run["hvac_off"]
                        else "Ventilation restored",
                    )

                st.rerun(scope="fragment")

            st.caption(
                "State: "
                + ("Isolated" if run["hvac_off"] else "Active")
            )

        with c2:
            if st.button(
                "Toggle simulated power",
                disabled=not run["active"],
                use_container_width=True,
            ):
                advance_run(run)

                if run["active"]:
                    run["power_off"] = not run["power_off"]
                    add_event(
                        run,
                        "Simulated power switched off"
                        if run["power_off"]
                        else "Simulated power restored",
                    )

                st.rerun(scope="fragment")

            st.caption(
                "State: " + ("Off" if run["power_off"] else "On")
            )

        with c3:
            if st.button(
                "End drill: suppression demo",
                disabled=not run["active"],
                use_container_width=True,
            ):
                advance_run(run)
                finish_run(run, "Ended by simulated suppression")
                st.rerun(scope="fragment")

            st.caption(
                "Ends the demonstration; does not model "
                "extinguishing-agent effectiveness."
            )

    with events_tab:
        st.dataframe(
            pd.DataFrame(run["events"]),
            use_container_width=True,
            hide_index=True,
        )

    with export_tab:
        st.download_button(
            "Download synthetic telemetry",
            data=pd.DataFrame(run["telemetry"]).to_csv(
                index=False
            ).encode("utf-8"),
            file_name=f"aeroguard_{run['id']}_telemetry.csv",
            mime="text/csv",
            key=f"telemetry_download_{run['id']}",
        )

        st.download_button(
            "Download event timeline",
            data=pd.DataFrame(run["events"]).to_csv(
                index=False
            ).encode("utf-8"),
            file_name=f"aeroguard_{run['id']}_events.csv",
            mime="text/csv",
            key=f"events_download_{run['id']}",
        )


def render_history():
    st.subheader("Session results")

    st.caption(
        "Results are stored in session memory, not a persistent database. "
        "Download completed results before leaving."
    )

    if not st.session_state.history:
        st.info("Complete or stop a drill to record its result.")
        return

    history = pd.DataFrame(st.session_state.history)

    st.dataframe(
        history,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download completed results",
        data=history.to_csv(index=False).encode("utf-8"),
        file_name="aeroguard_session_results.csv",
        mime="text/csv",
        key="history_download",
    )

    if len(history) >= 2:
        fig = px.bar(
            history,
            x="Run_ID",
            y="Final_Demo_Score",
            color="Material",
            title="Completed drill comparison",
            hover_data=[
                "Oxygen_pct",
                "Airflow_cm_s",
                "Elapsed_s",
                "Outcome",
            ],
        )

        fig.update_layout(
            template="plotly_dark",
            yaxis_title="Illustrative demo score",
            xaxis_title="Run",
        )

        st.plotly_chart(fig, use_container_width=True)


render_dashboard()


# ============================================================
# MODEL TRANSPARENCY AND REFERENCE VIEW
# ============================================================

st.divider()

with st.expander("Demonstration material table and 3D reference view"):
    st.caption(
        "Hard-coded illustrative values. These are not presented "
        "as verified NASA experimental observations."
    )

    st.dataframe(
        materials,
        use_container_width=True,
        hide_index=True,
    )

    fig_3d = px.scatter_3d(
        materials,
        x="Reference_Airflow",
        y="Reference_Oxygen",
        z="Reference_Heat",
        size="Reference_Spread",
        color="Category",
        hover_name="Material",
    )

    fig_3d.update_layout(
        template="plotly_dark",
        height=450,
        scene={
            "xaxis_title": "Reference airflow setting",
            "yaxis_title": "Reference oxygen setting",
            "zaxis_title": "Illustrative heat value",
        },
        margin={"l": 0, "r": 0, "t": 20, "b": 0},
    )

    st.plotly_chart(fig_3d, use_container_width=True)


with st.expander("Model assumptions and limitations"):
    st.markdown(
        """
        - Material values are illustrative.
        - Telemetry is synthetic, not measured.
        - Habitat and flight phase are labels, not physics inputs.
        - No gravity-dependent combustion equations are implemented.
        - The demo score is not physical damage or load capacity.
        - Power and ventilation effects are simplified assumptions.
        - Suppression ends the drill; it does not simulate agent physics.
        - No AI model or validated inverse optimizer is implemented.
        - No safe atmosphere or operational recommendation is produced.
        - No real hardware connection or user authentication is included.
        """
    )

    st.code(
        """
oxygen_multiplier = (oxygen_pct / 21.0) ** 1.85

flow_multiplier = (
    1.4
    if effective_airflow < 2.0
    else 1.0 + effective_airflow / 14.0
)

spread_proxy = (
    reference_spread
    * oxygen_multiplier
    * flow_multiplier
)

# If simulated power is off:
spread_proxy *= 0.35

# Accumulation uses elapsed time, not number of page reruns:
demo_score += spread_proxy * 0.12 * elapsed_seconds
""",
        language="python",
    )


st.caption(
    "AeroGuard Sim — experimental educational prototype. "
    "No NASA affiliation or operational approval is claimed."
)
