# 🎓 Virtual Spatiotemporal Air Quality Estimation System (Vidarbha Grid)

## Project Knowledge Base — Living Document

 *

## 📌 1. Problem Statement

Physical CPCB/MPCB air quality monitoring stations are **sparse and expensive**.

*   Semi-urban, industrial fringe, and rural Vidarbha areas remain **unmonitored**.
*   Simple IDW assumes linear pollution drop — wrong physics.
*   Satellite data (CAMS) has **coarse spatial resolution** (5×5 km) and can’t resolve local emission spikes.

**Goal**: Train an ML model that can **estimate real India NAQI at any unmonitored coordinate** using freely available satellite and weather data.

 *

## 🏗️ 2. Correct Architecture (Finalized 2026-10-10)

### The Core Insight

> Copernicus CAMS already provides PM2.5, PM10, NO2, etc. at any coordinate for free.  
> So predicting PM2.5 from CAMS data using CAMS data adds zero value.
> 
> The real value is: **learning the correction from what CAMS reports regionally  
> to what a CPCB physical station actually measures at ground level.**
> 
> CAMS misses: rush-hour traffic, road dust, boundary layer inversions,  
> industrial point source plumes at micro-scale (<5 km).

```java
Features (X)  ─────────────────────────────────────────────────────────────
  Copernicus CAMS  : PM2.5, PM10, NO2, SO2, CO, O3   (satellite grid ~5km)
  ECMWF ERA5       : Wind speed/dir, Temp, Humidity, Pressure, Radiation
  OpenStreetMap    : Road density, Highway counts (real road infrastructure)
  Spatial Physics  : Haversine distances, Downwind azimuth vectors

Target (y)  ────────────────────────────────────────────────────────────────
  WAQI / CPCB Physical Station : True ground-level India NAQI
  (max sub-index of all 6 pollutants, 24h rolling average, CPCB official)

What Model Learns  ─────────────────────────────────────────────────────────
  CAMS says PM2.5=40 at Nagpur + roads + wind physics
   => CPCB station actually measures NAQI=137
  The model learns this correction function.

At Prediction Time (unmonitored coordinate)  ───────────────────────────────
  Fetch CAMS + ERA5 + OSM for target lat/lon
   => Model predicts: estimated India NAQI at that coordinate
```

 *

## 🇮🇳 3. India NAQI Standard (CPCB Official)

India NAQI = **MAX** of all pollutant sub-indices:

```
NAQI = max(SubIndex_PM2.5, SubIndex_PM10, SubIndex_NO2,
           SubIndex_SO2,  SubIndex_CO,  SubIndex_O3)
```

Each sub-index is computed from a **24-hour rolling average** using CPCB breakpoints.

| NAQI Range | Category |
| :--- | :--- |
| 0 – 50 | Good |
| 51 – 100 | Satisfactory |
| 101 – 200 | Moderate |
| 201 – 300 | Poor |
| 301 – 400 | Very Poor |
| 401 – 500 | Severe |

> **Previous mistake**: We were predicting only `pm2_5` sub-index and calling it India NAQI.  
> That is wrong. India NAQI requires all 6 pollutants and takes the maximum.

 *

## 📡 4. Data Sources (Final Decision)

| Role | Source | URL | Coverage | Cost |
| :--- | :--- | :--- | :--- | :--- |
| **Target (y)** — Ground truth | **WAQI API** | `api.waqi.info` | Real-time CPCB station readings. Free token gives 48h history. | Free (token from [aqicn.org](http://aqicn.org)) |
| **Feature: Atm. Chemistry** | **Open-Meteo (CAMS)** | `air-quality-api.open-meteo.com` | Historical 2021-present. PM2.5, PM10, NO2, SO2, O3, CO at any coordinate | Free, no key |
| **Feature: Weather** | **Open-Meteo (ERA5)** | `api.open-meteo.com` | Historical 1940-present. Wind, Temp, Humidity, Pressure | Free, no key |
| **Feature: Road Network** | **OpenStreetMap Overpass** | `overpass-api.de` | Road topology, highway density | Free |
| **Feature: Spatial Physics** | **Computed** | — | Haversine distance, downwind vectors | Internal |

### Why WAQI for Ground Truth?

| Source | Real-Time | Historical | India CPCB Data | Free API | Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **WAQI** | ✅ Yes | ✅ 48h (free), full (paid) | ✅ Yes — direct CPCB feed | ✅ Free token | ✅ **CHOSEN** |
| OpenAQ v3 | ✅ Yes | ✅ Years | ⚠️ Partial — Vidarbha coverage gap | ✅ No key | ❌ Missing Vidarbha stations |
| CPCB CCR Portal | ✅ Yes | ✅ Years | ✅ Official | ❌ No public API | ❌ Requires scraping |
| Open-Meteo CAMS | ✅ Yes | ✅ Years | ❌ Satellite only, not ground | ✅ No key | ❌ Cannot be target (is feature) |

**OpenAQ v3 probe result**: 0 locations found for Nagpur, Chandrapur, Amravati, Akola.  
**WAQI with real token**: Fetches actual CPCB ground station readings for Vidarbha cities.

### WAQI Token Setup

1. Visit: https://aqicn.org/data-platform/token/
2. Register free account → get personal token
3. Set environment variable: WAQI_TOKEN=your_token_here
4. Demo token (demo) only works for one test station (Shanghai fallback).

 *

## 🗂️ 5. Modular Architecture & Execution Status

| Step | Core Objective | Key Deliverables | Status |
| :--- | :--- | :--- | :--- |
| **step\_01\_raw\_ingestion/** | Ingest CAMS (features) + WAQI CPCB (targets) | `weather_ingestion.py`, `air_quality_ingestion.py`, `cpcb_waqi_ingestion.py` (NEW) | **🔄 NEEDS UPDATE** |
| **step\_02\_preprocessing/** | Compute NAQI max sub-index, harmonics, OSM roads | `cleaner.py`, `osm_road_fetcher.py` | **🔄 NEEDS UPDATE** |
| **step\_03\_feature\_merge/** | Merge features + CPCB NAQI as target column | `merger.py`, `spatial_physics.py` | **🔄 NEEDS UPDATE** |
| **step\_04\_data\_split/** | Chronological + LOSO splits | `splitter.py` | **🔄 NEEDS UPDATE** |
| **step\_05\_batch\_and\_train/** | Train on X=CAMS+ERA5+Roads, y=CPCB\_NAQI | `trainer.py` | **⏭️ UPCOMING** |
| **step\_06\_validation/** | R², MAE, RMSE vs true CPCB NAQI | `evaluator.py` | **⏭️ UPCOMING** |
| **step\_07\_serialization/** | Package immutable model | `exporter.py` | **⏭️ UPCOMING** |
| **step\_08\_backend\_api/** | FastAPI `/predict?lat=&lon=` | `main.py` | **⏭️ UPCOMING** |

 *

## 💻 6. Operational Command Reference

```powershell
# Activate environment
cd d:\college_dev\ml
.\venv\Scripts\activate

# Set WAQI API token (get free token from https://aqicn.org/data-platform/token/)
$env:WAQI_TOKEN = "your_real_token_here"

# Step 01: Ingest features (CAMS + ERA5) + ground truth targets (WAQI/CPCB)
python step_01_raw_ingestion/collector.py --mode historical

# Step 02: Preprocess — compute NAQI max sub-index, harmonics, OSM
python step_02_preprocessing/cleaner.py

# Step 03: Merge all into master analytical matrix
python step_03_feature_merge/merger.py

# Step 04: Chronological + LOSO split
python step_04_data_split/splitter.py

# Step 05: Train (upcoming)
python step_05_batch_and_train/trainer.py
```

 *

## 📊 7. Dataset Registry (Post-Redesign)

| File | Description | Rows | Cols |
| :--- | :--- | :--- | :--- |
| `data/raw/weather/weather_vidarbha_combined.csv` | ERA5 weather features | 35,040 | 15 |
| `data/raw/air_quality/air_quality_vidarbha_combined.csv` | CAMS features (pm2\_5, pm10, no2…) | 35,040 | 11 |
| `data/raw/cpcb_ground_truth/cpcb_naqi_vidarbha.csv` | **NEW** WAQI/CPCB actual NAQI readings | Variable | 8 |
| `data/raw/real_osm_road_network.json` | OSM road counts | 4 stations | — |
| `data/clean/master_analytical_matrix.csv` | All features + `india_naqi_ground` target | ~35,040 | ~55 |

 *

## 🎯 8. Next Immediate Step: Step 01 Update

Add `cpcb_waqi_ingestion.py` to `step_01_raw_ingestion/`:

*   Takes a free WAQI token from `WAQI_TOKEN` env variable
*   Fetches historical CPCB NAQI readings for all 4 Vidarbha stations
*   Saves to `data/raw/cpcb_ground_truth/cpcb_naqi_vidarbha.csv`
*   Re-run steps 02, 03, 04 with `india_naqi_ground` as the target column `y`

 *

## 📋 9. Key Technical Decisions Log

| Date | Decision | Rationale |
| :--- | :--- | :--- |
| 2026-10-10 | Use WAQI CPCB ground data as target (y) | Only source with real-time + historical CPCB physical readings for Vidarbha |
| 2026-10-10 | Use India NAQI max sub-index (all 6 pollutants) | CPCB official standard; PM2.5-only is scientifically wrong |
| 2026-10-10 | Use CAMS + ERA5 + OSM as features (X) | Available at ANY coordinate for inference at unmonitored locations |
| 2026-10-10 | Rejected OpenAQ v3 | 0 Vidarbha stations found in probe |
| 2026-10-10 | Rejected CPCB CCR Portal | No public API; scraping is fragile |
| Earlier | Rejected synthetic data | User mandate: real data only |
| Earlier | Rejected CAMS as target | CAMS is already a feature; predicting it from itself adds no value |