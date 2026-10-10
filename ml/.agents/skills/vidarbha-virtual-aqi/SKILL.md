---
name: vidarbha-virtual-aqi
description: >
  Virtual Spatiotemporal Air Quality Estimation System for Vidarbha (Maharashtra).
  ML pipeline that predicts true India NAQI at unmonitored coordinates.
  Supervised Training on CPCB Ground Stations (Nagpur + Chandrapur, 17,520 rows).
  Deployment / Virtual Sensor evaluation on unmonitored cities (Amravati + Akola, 17,520 rows).
  Features (X) = Copernicus CAMS + ECMWF ERA5 + OpenStreetMap + Spatial Physics.
  8-step modular pipeline from ingestion to FastAPI deployment.
---

# Vidarbha Virtual Spatiotemporal Air Quality Grid

## ⚡ Quick Orientation
- **Goal**: Predict true India NAQI at any unmonitored coordinate across Vidarbha.
- **Why not predict PM2.5?** Copernicus CAMS already provides PM2.5, PM10, NO2, etc. at any coordinate. Predicting satellite PM2.5 from satellite features adds zero real value.
- **True Value Proposition**: The model learns the residual correction function from coarse satellite reanalysis (5×5 km grid) to actual ground-level CPCB/MPCB monitoring stations (which capture micro-scale traffic spikes, road dust, and boundary layer trapping).
- **Data Integrity**: Clean supervised training on monitored stations (`NAGPUR_CENTRAL`, `CHANDRAPUR_MIDC`, 17,520 rows) without label contamination. Unmonitored cities (`AMRAVATI_CENTRAL`, `AKOLA_WEST`, 17,520 rows) serve as deployment target sets.

## 🏗️ Model Architecture
```
Features (X, 49 columns):              Target (y):
  CAMS:  PM2.5, PM10, NO2, SO2, CO, O3    CPCB Physical Station NAQI
  ERA5:  Wind, Temp, Humidity, Pressure      (max sub-index, all 6 pollutants)
  OSM:   Road density, Highway counts        (CPCB official standard)
  Phys:  Downwind vectors, distances
         ↓
     [LightGBM / XGBoost Regressor]
         ↓
     Estimated Ground-Level India NAQI at any coordinate
```

## 🇮🇳 India NAQI Standard
`NAQI = max(SubIdx_PM2.5, SubIdx_PM10, SubIdx_NO2, SubIdx_SO2, SubIdx_CO, SubIdx_O3)`
Categories: Good (0-50) | Satisfactory (51-100) | Moderate (101-200) | Poor (201-300) | Very Poor (301-400) | Severe (401-500)

## 📡 Data Ingestion & Authentic Sources
- **Features (X)**: Copernicus CAMS + ECMWF ERA5 via Open-Meteo (real atmospheric data at any coordinate).
- **Physical Roads**: Real OpenStreetMap Overpass road segment counts.
- **Target (y)**: WAQI / CPCB Physical Ground Station Feed (`api.waqi.info`) using authentic token from `.env`.
- **Stations**:
  - Nagpur: Opp GPO Civil Lines (UID: 12444 / 8824) - *Monitored Ground Truth*
  - Chandrapur: MIDC Khutala (UID: 9147) - *Monitored Ground Truth*
  - Amravati & Akola: *Unmonitored Virtual Sensor Target Nodes*

## 🗂️ Pipeline Execution Steps
1. `step_01_raw_ingestion/`: Ingest CAMS + ERA5 + CPCB ground truth.
2. `step_02_preprocessing/`: Compute official India NAQI max sub-index, cyclic temporal transforms, OSM road density.
3. `step_03_feature_merge/`: Merge on `[timestamp + station_id]`, append spatial physics (Haversine & downwind dispersion).
4. `step_04_data_split/`: Partition monitored ground training (17,520 rows) + unmonitored deployment set (17,520 rows).
5. `step_05_batch_and_train/`: Fit LightGBM and XGBoost models (COMPLETE - Champion: XGBoost R²=0.9690).
6. `step_06_validation/`: Benchmarks vs IDW baseline (COMPLETE - 93.1% error reduction over IDW).
7. `step_07_serialization/`: Package immutable artifacts (COMPLETE - `pipeline_model.joblib` 4.87 MB).
8. `step_08_backend_api/`: FastAPI microservice and interactive map interface.
