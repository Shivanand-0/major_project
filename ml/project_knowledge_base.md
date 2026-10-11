# 🎓 Virtual Spatiotemporal Air Quality Estimation System (Vidarbha Grid)

## Project Knowledge Base — Living Document

## 📌 1. Problem Statement

Physical CPCB/MPCB air quality monitoring stations are **sparse and expensive**.

*   Semi-urban, industrial fringe, and rural Vidarbha areas remain **unmonitored**.
*   Simple IDW assumes linear pollution drop — wrong physics.
*   Satellite data (CAMS) has **coarse spatial resolution** (5×5 km) and can’t resolve local emission spikes.

**Goal**: Train an ML model that can **estimate real India NAQI at any unmonitored coordinate** using freely available satellite and weather data.

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

## 📊 7. Dataset Registry (Post-Redesign)

| File | Description | Rows | Cols |
| :--- | :--- | :--- | :--- |
| `data/raw/weather/weather_vidarbha_combined.csv` | ERA5 weather features | 35,040 | 15 |
| `data/raw/air_quality/air_quality_vidarbha_combined.csv` | CAMS features (pm2\_5, pm10, no2…) | 35,040 | 11 |
| `data/raw/cpcb_ground_truth/cpcb_naqi_vidarbha.csv` | **NEW** WAQI/CPCB actual NAQI readings | Variable | 8 |
| `data/raw/real_osm_road_network.json` | OSM road counts | 4 stations | — |
| `data/clean/master_analytical_matrix.csv` | All features + `india_naqi_ground` target | ~35,040 | ~55 |

## 🎯 8. Next Immediate Step: Step 01 Update

Add `cpcb_waqi_ingestion.py` to `step_01_raw_ingestion/`:

*   Takes a free WAQI token from `WAQI_TOKEN` env variable
    
*   Fetches historical CPCB NAQI readings for all 4 Vidarbha stations
    
*   Saves to `data/raw/cpcb_ground_truth/cpcb_naqi_vidarbha.csv`
    
*   Re-run steps 02, 03, 04 with `india_naqi_ground` as the target column `y`
    

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

\====================================================

\====================================================

\====================================================

 Restructuring Complete (Steps 1, 2, and 3)

The codebase across **Step 01**, **Step 02**, and **Step 03** has been restructured with single-responsibility modularity, zero redundant files, and clean documentation.

### Summary of Improvements

#### 1\. Single Responsibility Architecture

*   **\[`naqi.py`\](file:///d:/college\_dev/ml/step\_01\_raw\_ingestion/naqi.py)**: Extracted all official CPCB breakpoint tables, piecewise linear sub-index interpolation, composite NAQI calculation, and health category classifications into a dedicated module.
    
*   **\[`config.py`\](file:///d:/college\_dev/ml/step\_01\_raw\_ingestion/config.py)**: Single source of truth for all paths (`data/raw/`, `data/clean/`, etc.), station coordinates, date ranges, and API parameters. Removed duplicate `config.py` files across steps 2 and 3.
    
*   **\[`weather_ingestion.py`\](file:///d:/college\_dev/ml/step\_01\_raw\_ingestion/weather\_ingestion.py)**: Unified historical ERA5 archive ingestion and real-time live ingestion into a configurable interface without hardcoded year constants.
    
*   **\[`air_quality_ingestion.py`\](file:///d:/college\_dev/ml/step\_01\_raw\_ingestion/air\_quality\_ingestion.py)**: Dedicated CAMS satellite air quality ingestion without duplicate breakpoint code.
    
*   **\[`cpcb_ground_truth.py`\](file:///d:/college\_dev/ml/step\_01\_raw\_ingestion/cpcb\_ground\_truth.py)**: Dedicated live scraper for official CPCB portal (`app.cpcbccr.com`) with WAQI API fallback.
    
*   **\[`cpcb_bulk_ingestion.py`\](file:///d:/college\_dev/ml/step\_01\_raw\_ingestion/cpcb\_bulk\_ingestion.py)**: Dedicated downloader for OpenAQ S3 public archives for continuous multi-year physical analyzer data.
    
*   **\[`osm_road_fetcher.py`\](file:///d:/college\_dev/ml/step\_01\_raw\_ingestion/osm\_road\_fetcher.py)**: OpenStreetMap Overpass API road infrastructure metrics.
    
*   **\[`collector.py`\](file:///d:/college\_dev/ml/step\_01\_raw\_ingestion/collector.py)**: Ingestion orchestrator coordinating all data streams. Fixed previous latitude/longitude metadata indexing.
    
*   **\[`cleaner.py`\](file:///d:/college\_dev/ml/step\_02\_preprocessing/cleaner.py)**: Unified Step 02 preprocessor handling temporal sorting, linear interpolation, wind vector decomposition, cyclic temporal encodings, and combustion tracer ratios.
    
*   **\[`merger.py`\](file:///d:/college\_dev/ml/step\_03\_feature\_merge/merger.py)** & **\[`spatial_physics.py`\](file:///d:/college\_dev/ml/step\_03\_feature\_merge/spatial\_physics.py)**: Dedicated matrix construction and atmospheric physics calculations (Haversine distance, inverse distance weighting, wind alignment azimuth, downwind dispersion).
    

#### 2\. Redundancy & Dead Code Removed

*   Deleted **`step_01/spatiotemporal_match_2025.py`** (was duplicate of weather/AQ ingestion).
    
*   Deleted **`step_02/clean_spatiotemporal_2025.py`** and **`step_02/diagnose_discrepancy.py`**.
    
*   Deleted redundant redirect shim **`step_02/osm_road_fetcher.py`**.
    
*   Deleted **`step_02/config.py`** and **`step_03/config.py`**.
    
*   Deleted **`step_03/merge_spatiotemporal_2025.py`**.
    
*   Removed outdated readme scratchpads (`command_readme.md`, `info_readme.md`).
    

#### 3\. Clear Documentation & Data Catalog

*   Created **\[`ml/data/README.md`\](file:///d:/college\_dev/ml/data/README.md)**: Details the complete directory hierarchy (`raw/`, `clean/`, `split/`, `models/`, `validation/`), field definitions, data sources, and authenticity policies.
    
*   Updated **\[`ml/step_01_raw_ingestion/README.md`\](file:///d:/college\_dev/ml/step\_01\_raw\_ingestion/README.md)**, **\[`ml/step_02_preprocessing/README.md`\](file:///d:/college\_dev/ml/step\_02\_preprocessing/README.md)**, and **\[`ml/step_03_feature_merge/README.md`\](file:///d:/college\_dev/ml/step\_03\_feature\_merge/README.md)** to reflect the updated modules and execution workflows.
    

#### 4\. Verification & Compatibility

*   Verified that all modules import cleanly:
    
    *   `step_01_raw_ingestion`
    *   `step_02_preprocessing`
    *   `step_03_feature_merge`
    *   `step_04_data_split`
    *   `step_05_batch_and_train`
    *   `step_06_validation`
    *   `step_07_serialization`
    *   `backend.services.estimator`
*   Tested NAQI sub-index computation against official CPCB breakpoints:
    
    *   $\text{PM}_{2.5} = 30\,\mu\text{g/m}^3 \rightarrow 50.0$ (Good)
    *   $\text{PM}_{2.5} = 60\,\mu\text{g/m}^3 \rightarrow 100.0$ (Satisfactory)
    *   $\text{PM}_{2.5} = 120\,\mu\text{g/m}^3 \rightarrow 300.0$ (Poor)
    *   $\text{PM}_{10} = 150\,\mu\text{g/m}^3 \rightarrow 134.0$ (Moderate)

  

### What Was Done

#### 1\. Added Physical CPCB Ground Truth for Akola & Amravati

Located the official CPCB / MPCB CAAQMS continuous analyzer stations on the OpenAQ Public S3 archive:

*   **Akola**: Location ID `3409456` (`Ramdaspeth, Akola - MPCB`, `20.719516, 77.000253`)
*   **Amravati**: Location ID `3409458` (`Shivneri Colony, Amravati - MPCB`, `20.940236, 77.789525`)
*   **Nagpur**: Location ID `5621` (`Civil Lines / Opp GPO, Nagpur - MPCB`, `21.152875, 79.051753`)
*   **Chandrapur**: Location ID `5565` (`MIDC Khutala, Chandrapur - MPCB`, `19.977530, 79.233709`)

All **4 physical stations** now download real hourly continuous analyzer data.

#### 2\. Updated \[`collector.py`\](file:///d:/college\_dev/ml/step\_01\_raw\_ingestion/collector.py) Historical Mode

Running `collector.py --mode historical` now orchestrates all 4 data sources into one execution:

1. Phase 1/4: [weather_ingestion.py](file:///d:/college_dev/ml/step_01_raw_ingestion/weather_ingestion.py) — ECMWF ERA5 reanalysis for all stations.
2. Phase 2/4: [air_quality_ingestion.py](file:///d:/college_dev/ml/step_01_raw_ingestion/air_quality_ingestion.py) — Copernicus CAMS atmospheric chemistry tracers.
3. Phase 3/4: [cpcb_bulk_ingestion.py](file:///d:/college_dev/ml/step_01_raw_ingestion/cpcb_bulk_ingestion.py) — Continuous physical analyzer ground truth for all 4 stations (Nagpur, Chandrapur, Amravati, Akola).
4. Phase 4/4: [osm_road_fetcher.py](file:///d:/college_dev/ml/step_01_raw_ingestion/osm_road_fetcher.py) — OpenStreetMap infrastructure road counts and density.

### Commands to Run and Test

#### 1. Ingest All Historical Data (Weather, CAMS, CPCB for all 4 stations, OSM)

```powershell
& "d:\college_dev\ml\venv\Scripts\python.exe" ml/step_01_raw_ingestion/collector.py --mode historical --year 2025
```

#### 2. Run Step 02 (Preprocessing & Feature Engineering)

```powershell
& "d:\college_dev\ml\venv\Scripts\python.exe" ml/step_02_preprocessing/cleaner.py
```

#### 3. Run Step 03 (Master Matrix Merge with Spatial Physics)

```powershell
& "d:\college_dev\ml\venv\Scripts\python.exe" ml/step_03_feature_merge/merger.py
```

#### 4. Run Step 04 (Seasonal Block Data Partitioning)

```powershell
& "d:\college_dev\ml\venv\Scripts\python.exe" ml/step_04_data_split/splitter.py
```
- **Partition:** Days 1-20 Train (64.1%), Days 21-25 Val (17.6%), Days 26-End Test (18.3%).
- **Schema:** 42 features (pruned static distance proxies; retained dynamic wind alignment and dispersion physics vectors).

#### 5. Run Step 05 (Batch & Train Multi-Model Engine)

```powershell
& "d:\college_dev\ml\venv\Scripts\python.exe" ml/step_05_batch_and_train/trainer.py
```
- **Champion:** LightGBM Regressor (`LGBMRegressor`, 529 iterations, $R^2 = 0.5765$, MAE = $22.61$ AQI).
- **LOSO Spatial Transfer:** Evaluated zero-shot spatial transfer across all 4 cities ($R^2$ up to $0.493$).

#### 6. Run Step 06 (Diagnostic Validation Engine)

```powershell
& "d:\college_dev\ml\venv\Scripts\python.exe" ml/step_06_validation/evaluator.py
```
- **Test Metrics:** $R^2 = 0.5765$, MAE = $22.61$ AQI points, Pearson $r = 0.7638$.
- **Baseline Comparison:** Beats traditional Inverse Distance Weighting across all 4 stations.

#### 7. Run Step 07 (Serialization & Live Real-Time Validation)

```powershell
# 1. Package and export production pipeline bundle
& "d:\college_dev\ml\venv\Scripts\python.exe" ml/step_07_serialization/exporter.py

# 2. Run live real-time validation against live telemetry & CPCB feeds
& "d:\college_dev\ml\venv\Scripts\python.exe" ml/step_07_serialization/realtime_validator.py
```
- **Production Bundle:** `data/models/pipeline_model.joblib` (1.02 MB)
- **Live Output:** `data/validation/realtime_validation_report.json`