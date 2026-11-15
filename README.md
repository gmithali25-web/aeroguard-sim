# 🛰️ AeroGuard: Autonomous Microgravity Fire Guardian & 3D Flight Simulator

AeroGuard is a next-generation microgravity fire-safety monitoring and rocket flight simulation platform designed for research scholars, astronauts, and flight controllers. Built with scientific rigor, it integrates **NASA PSI-117 combustion reference datasets**, real-time anomaly tracking, and interactive 3D visualizations.

---

## ✨ Key Features

1. **Multi-Provider OAuth Gateway**: Secure simulation access supporting Google, Twitter (X), and Guest Controller sign-ins.
2. **Surface & Structural Damage Assessment**: Real-time pyrolytic mass loss, charring depth calculations, and load capacity degradation tracking.
3. **Live Sensor Stream**: Carbon Monoxide (CO ppm) and optical smoke obscuration monitoring.
4. **3D Flammability Phase Space**: Interactive Plotly 3D scatter plots mapping airflow, ambient oxygen percentage, and radiative heat flux against quench difficulty.
5. **Hardware Overrides**: Emergency interlocks for HVAC damper isolation, rack power cutoff, and water-mist suppression.
6. **AI Guardian Physicist & Reverse Optimizer**: Reverse-calculates safe ambient operational parameters based on user-defined damage thresholds.
7. **Google Colab & GitHub Integration**: Built-in pipeline guidance for validating NASA datasets and syncing simulation logs.

---

## 🚀 Running via Google Colab

To run and test AeroGuard instantly inside Google Colab:

1. Create a new notebook and install dependencies:
   ```bash
   !pip install -r requirements.txt
