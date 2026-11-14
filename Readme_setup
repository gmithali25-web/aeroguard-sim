AEROGUARD v6.0 — SETUP GUIDE
==============================

FILES
-----
app.py             Main Streamlit application
requirements.txt   Python package dependencies
aeroguard_v6.sqlite3  Created automatically when the app runs

INSTALLATION (Windows)
----------------------
1. Create a folder named AeroGuard_v6.
2. Put app.py and requirements.txt inside that same folder.
3. Open Command Prompt in that folder.
4. (Recommended) Create a virtual environment:

   py -m venv .venv
   .venv\Scripts\activate

5. Install dependencies:

   py -m pip install -r requirements.txt

6. Start the app:

   py -m streamlit run app.py

7. The browser should open the AeroGuard dashboard. Click "Enter AeroGuard Demo".

INSTALLATION (macOS / Linux)
----------------------------
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py

IMPORTANT NOTES
---------------
- Do not paste requirements.txt lines into app.py. They are separate files.
- Back up your old app.py and old SQLite database before replacing anything.
- The v6 database is named aeroguard_v6.sqlite3. The previous v5 database is not
  automatically migrated; keep it as a backup.
- If Streamlit reports a missing module, rerun the pip install command using the
  same Python launcher/environment used to start Streamlit.
- To stop the app, press Ctrl+C in the terminal.

WHAT V6.0 ADDS
--------------
1. Explainable multi-sensor rule fusion and sensor coverage reporting.
2. Synthetic sensor fault injection: disconnected, stuck, drifted and offset channels.
3. Short-horizon linear trend projection with residual spread.
4. Virtual response strategy comparison.
5. Conceptual 2D/3D habitat digital twin views.
6. Scenario snapshot save and replay using SQLite.
7. Repeatable synthetic benchmark suite with TP/TN/FP/FN counts.
8. Persistent audit, telemetry and scenario exports.

SAFETY / VALIDATION
-------------------
This is a research and demonstration simulator only. It does not connect to physical
sensors or actuators. It is not certified flight software, a validated fire model,
a crew procedure, or a real emergency decision system. Do not use its outputs to
operate real aerospace, aircraft, life-support, fire-suppression or power equipment.

The material reference rows were inherited from the supplied AeroGuard code. They
are labelled as application sample data and are not independently verified NASA data.
