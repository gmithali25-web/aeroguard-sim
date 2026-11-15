FILES
-----
app.py
requirements.txt

RUN ON WINDOWS
--------------
1. Put app.py and requirements.txt in the same folder.
2. Open Command Prompt in that folder.
3. Run:
   py -m venv .venv
   .venv\Scripts\activate
   py -m pip install -r requirements.txt
   py -m streamlit run app.py

RUN ON macOS / LINUX
--------------------
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py

WHAT IS INCLUDED
----------------
- Dark aerospace mission-control visual design.
- Mission Dashboard.
- Combustion Explorer with CSV upload and clearly labelled illustrative demo records.
- Demonstration Particle Swarm Optimization on a mathematical test function.
- Fire Safety Insights research-question workspace.
- 0–90,000 ft simplified layered standard-atmosphere explorer.
- Parameterized aerodynamic calculator with explicit model limitations.
- Research source register.

SCIENTIFIC LIMITATIONS
----------------------
- Built-in combustion rows are synthetic interface demo data, NOT NASA measurements.
- PSO currently demonstrates optimizer mechanics on a mathematical objective; it does
  NOT claim to discover combustion laws.
- The atmosphere module is a simplified educational standard-atmosphere implementation.
- The aerothermal calculation is a preliminary correlation indicator and is not a
  validated SLS heating prediction.
- No live spacecraft, satellite, NASA telemetry, or hardware connections exist.
- The SLS details are reference context, not live telemetry or a full trajectory model.

NEXT INTEGRATION STEPS
----------------------
1. Import verified NASA PSI/FLEX files and preserve provenance.
2. Define and validate a combustion-specific PSO fitness function.
3. Obtain adequate SLS stage/thrust/aerodynamic inputs for trajectory reconstruction.
4. Validate atmospheric, aerodynamic and thermal calculations against authoritative
   reference cases before using results in research conclusions.
