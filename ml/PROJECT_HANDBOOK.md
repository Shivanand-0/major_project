# 🎓 Virtual Spatiotemporal Air Quality Estimation System (Vidarbha Grid)

## Complete Technical Documentation & Handover Handbook

 *

## 📌 1. Project Blueprint & Architectural Rationale

### The Problem

Physical air quality monitoring stations (CPCB/MPCB) are capital-intensive and sparse across Vidarbha (Nagpur, Chandrapur, Amravati, Akola).

*   Unmonitored semi-urban and rural areas lack accurate ground truth.
*   Coarse satellite grids (Copernicus CAMS at ~5×5 km) give regional background levels but fail to capture local micro-emission spikes (traffic congestion, road dust, biomass burning, and thermal power plant plumes).

### The Scientific Paradigm

*   **Features ($X$)**: Universally accessible anywhere on Earth without physical sensors:
    
    1. Copernicus CAMS Reanalysis (Atmospheric chemical tracers: PM2.5​,PM10​,NO2​,SO2​,CO,O3​).
    2. ECMWF ERA5 Meteorology (Wind velocity & direction, boundary layer pressure, humidity, thermal gradients).
    3. Real OpenStreetMap Road Infrastructure (Highway segment counts, intersection density).
    4. Atmospheric Transport Physics (Haversine geodesic proximity & downwind dispersion vectors).
    
*   **Target Label ($y$)**: Real physical ground-truth measurements from **CPCB/MPCB monitoring stations** (via WAQI authentic live/historical API).
*   **India NAQI Standard**: Computed strictly using the Central Pollution Control Board (CPCB) official maximum sub-index formulation:

$$
\text{NAQI} = \max\Big(\text{SubIndex}_{\text{PM}_{2.5}}, \text{SubIndex}_{\text{PM}_{10}}, \text{SubIndex}_{\text{NO}_2}, \text{SubIndex}_{\text{SO}_2}, \text{SubIndex}_{\text{CO}}, \text{SubIndex}_{\text{O}_3}\Big)
$$

*   **What the Model Learns**: The transfer function mapping coarse satellite & weather physics to real ground-level CPCB NAQI, resolving micro-scale biases for unmonitored coordinates.

 *

## 🗺️ 2. Modular Architecture & Execution Status

| Step Folder | Core Objective | Key Deliverables | Status |
| :--- | :--- | :--- | :--- |
| **`step_01_raw_ingestion/`** | Ingest CAMS + ERA5 features and CPCB ground-truth station data via WAQI. | `weather_ingestion.py`, `air_quality_ingestion.py`, `cpcb_ground_truth.py`, `collector.py` | **✅ UPDATED** |
| **`step_02_preprocessing/`** | Multi-pollutant India NAQI max sub-index computation, cyclic time transforms, OSM road density. | `cleaner.py`, `osm_road_fetcher.py` | **✅ COMPLETE** |
| **`step_03_feature_merge/`** | Compound index join on `[timestamp + station_id]`, spatial distance & downwind physics. | `spatial_physics.py`, `merger.py` (`master_analytical_matrix.csv`) | **✅ COMPLETE** |
| **`step_04_data_split/`** | Leakage-free Chronological Window Cut & Spatial Leave-One-Station-Out (LOSO) sets. | `splitter.py` | **✅ COMPLETE** |
| **`step_05_batch_and_train/`** | Fit LightGBM and XGBoost regressors on fused features. Champion selection. | `train_lgbm.py`, `train_xgboost.py`, `trainer.py` (`champion_model.joblib`) | **✅ COMPLETE (XGBoost R²: 0.9690, MAE: 6.01)** |
| **`step_06_validation/`** | Residual analysis, error distributions, and IDW spatial interpolation comparison. | `evaluator.py`, `idw_baseline.py` (`validation_report.json`) | **✅ COMPLETE (93.1% error reduction vs IDW)** |
| **`step_07_serialization/`** | Package immutable model weights, schema, and production pipeline. | `exporter.py`, `inference_engine.py` (`pipeline_model.joblib`) | **✅ COMPLETE (Production Artifact: 4.87 MB)** |
| **`step_07_serialization/` (7.2)** | Real-time live validation: Query live CAMS + weather + WAQI feeds for instantaneous benchmarking. | `realtime_validator.py` (`realtime_validation_report.json`) | **✅ COMPLETE (Live Ingestion & Verification Validated)** |
| **`backend/` (Step 08)** | Production FastAPI microservice (`/api/nodes`, `/api/predict`, `/api/grid`) + Modern Interactive Web Dashboard. | `backend/main.py`, `backend/services/estimator.py`, `backend/static/` | **✅ COMPLETE (Live on :8000)** |

---

## 💻 3. Operational Command Reference

### Activating the Environment:

```powershell
cd d:\college_dev\ml
.\venv\Scripts\activate
```

### Loading Environment Variables:

The official WAQI token and data.gov.in API keys are stored in `d:\college_dev\.env`:

```powershell
# In PowerShell:
Get-Content d:\college_dev\.env | ForEach-Object { if ($_ -match "WAQI_TOKEN\s*=\s*\"(.*)\"") { $env:WAQI_TOKEN = $matches[1] } }
```

### Pipeline Execution Sequence:

```powershell
# 1. Step 01 - Raw Ingestion (CAMS + ERA5 + CPCB Feeds)
python step_01_raw_ingestion/collector.py --mode historical

# 2. Step 02 - Preprocessing (NAQI Sub-Indices, Cyclic Harmonics, OSM Roads)
python step_02_preprocessing/cleaner.py

# 3. Step 03 - Feature Merge (Master Matrix & Spatial Atmospheric Physics)
python step_03_feature_merge/merger.py

# 4. Step 04 - Data Split (Chronological Cut & Spatial LOSO Partitioning)
python step_04_data_split/splitter.py

# 5. Step 05 - Batch & Train (Fit LightGBM & XGBoost, Select Champion)
python step_05_batch_and_train/trainer.py

# 6. Step 06 - Offline Validation & Baseline Benchmarking (Residuals & IDW Comparison)
python step_06_validation/evaluator.py
python step_06_validation/idw_baseline.py

# 7. Step 07 - Model Serialization & Production Pipeline Packaging
python step_07_serialization/exporter.py
python step_07_serialization/inference_engine.py

# 8. Step 07.2 - Real-Time Live Ground Truth & Satellite Validation
# Test authentic CPCB live portal ingestion:
python step_01_raw_ingestion/cpcb_ground_truth.py

# Execute full end-to-end live real-time validation test:
python step_07_serialization/realtime_validator.py

# 9. Step 08 - Production Backend API & Interactive Geospatial Dashboard
cd d:\college_dev
.\ml\venv\Scripts\python.exe backend\run.py
# Open in browser: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## 📊 4. Dataset & Model Artifact Registry

*   `data/raw/weather/weather_vidarbha_combined.csv` (ERA5 meteorological parameters)
*   `data/raw/air_quality/air_quality_vidarbha_combined.csv` (CAMS chemical tracers)
*   `data/raw/real_osm_road_network.json` (Real OpenStreetMap highway counts)
*   `data/clean/master_analytical_matrix.csv` (35,040 rows × 53 features)
*   `data/split/split_metadata.json` (Chronological & spatial LOSO partition indices)
*   `data/models/champion_model.joblib` (Champion model artifact — XGBoost Regressor)
*   `data/models/lgbm_model.joblib` (LightGBM trained model)
*   `data/models/pipeline_model.joblib` (Self-contained production pipeline artifact — 4.87 MB)
*   `data/models/training_benchmark_report.json` (Comparative evaluation report)
*   `data/validation/validation_report.json` (Step 06 detailed evaluation metrics)
*   `data/validation/idw_benchmark_report.json` (Spatial IDW comparison report — 93.1% error reduction)
*   `data/validation/realtime_validation_report.json` (Step 07.2 live CPCB vs. Virtual Sensor validation report)