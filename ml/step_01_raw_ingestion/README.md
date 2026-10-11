# Step 01: Authentic Raw Data Ingestion

## 1. Objective & Scope
The goal of Step 01 is to collect **100% authentic, scientifically validated raw datasets** across the Vidarbha Air Quality Monitoring Grid (Nagpur, Chandrapur, Amravati, Akola).
**Core Mandate:**
- Support both **historical archive extraction** (calendar windows like 2023–2024) and **instantaneous live real-time ingestion**.
- **Zero synthetic approximations**, zero simulated noise, and zero fallback estimations. All records originate from operational satellite reanalyses, atmospheric physics models, ground monitoring stations, and real GIS networks.

---

## 2. Architecture & File Breakdown

Step 01 consists of the following modular collectors:

| File | Primary Source | Scientific Authority | Output Storage |
| :--- | :--- | :--- | :--- |
| [`weather_ingestion.py`](file:///d:/college_dev/ml/step_01_raw_ingestion/weather_ingestion.py) | ECMWF ERA5 & ERA5-Land Reanalysis / Open-Meteo | European Centre for Medium-Range Weather Forecasts | `data/raw/weather/` |
| [`air_quality_ingestion.py`](file:///d:/college_dev/ml/step_01_raw_ingestion/air_quality_ingestion.py) | Copernicus Atmosphere Monitoring Service (CAMS) | European Earth Observation Programme | `data/raw/air_quality/` |
| [`cpcb_ground_truth.py`](file:///d:/college_dev/ml/step_01_raw_ingestion/cpcb_ground_truth.py) | Official CPCB CCR Portal (`app.cpcbccr.com`), WAQI fallback | Central Pollution Control Board & MPCB | `data/raw/cpcb_ground_truth/` |
| [`cpcb_bulk_ingestion.py`](file:///d:/college_dev/ml/step_01_raw_ingestion/cpcb_bulk_ingestion.py) | OpenAQ Public S3 Archive (`s3://openaq-data-archive/`) | Continuous physical CAAQMS analyzer data | `data/raw/cpcb_ground_truth/` |
| [`naqi.py`](file:///d:/college_dev/ml/step_01_raw_ingestion/naqi.py) | Official CPCB NAQI Breakpoint Standard | Central Pollution Control Board guidelines | Internal computation |
| [`osm_road_fetcher.py`](file:///d:/college_dev/ml/step_01_raw_ingestion/osm_road_fetcher.py) | OpenStreetMap Overpass API | OpenStreetMap Foundation | `data/raw/osm_roads/` |
| [`collector.py`](file:///d:/college_dev/ml/step_01_raw_ingestion/collector.py) | **Master Ingestion Orchestrator** | Coordinates historical batch and live streams | `data/raw/` |
| [`config.py`](file:///d:/college_dev/ml/step_01_raw_ingestion/config.py) | Centralized Configuration & Station Registry | Vidarbha Station Registry | N/A |

> [!NOTE]
> **Spatial Physics Formulation:**  
> Spatial geodesic distances, wind transport azimuth angles, and inverse-distance weighting are formulated as analytical features. These belong to **Step 03 (`step_03_feature_merge/spatial_physics.py`)**, which consumes the raw station coordinates and road metrics collected here.

---

## 3. Data Ingestion Modes

### A. Historical Mode (Training & Benchmarking Pipeline)
Collects full hourly time-series for all 4 Vidarbha grid stations for model training:
```bash
python ml/step_01_raw_ingestion/collector.py --mode historical --start-date 2023-01-01 --end-date 2023-12-31
```
- **Weather dataset:** 35,040 rows $\times$ 15 parameters (`data/raw/weather/weather_vidarbha_combined.csv`)
- **Air Quality dataset:** 35,040 rows $\times$ 11 parameters (`data/raw/air_quality/air_quality_vidarbha_combined.csv`)
- **OSM Road Infrastructure:** Road segments and classification counts (`data/raw/osm_roads/osm_road_network.json`)

### B. Live Real-Time Mode (Production Telemetry Ingestion)
Fetches current instantaneous meteorology, Copernicus atmospheric chemistry, physical ground truth, and OSM context for any coordinate:
```bash
python ml/step_01_raw_ingestion/collector.py --mode live --lat 21.1458 --lon 79.0882
```
- Outputs instantaneous snapshot to `data/raw/live_telemetry_snapshot.json` and updates `data/raw/cpcb_ground_truth/live_cpcb_snapshot.json`.

---

## 4. Raw Parameters & Scientific Descriptions

### Meteorology (ECMWF ERA5)
- `temperature_2m` (°C): Ambient dry-bulb temperature at 2m.
- `relative_humidity_2m` (%): Atmospheric moisture saturation percentage.
- `dew_point_2m` (°C): Condensation threshold temperature at 2m.
- `surface_pressure` (hPa): Local barometric pressure at surface elevation.
- `wind_speed_10m` (km/h) & `wind_direction_10m` (deg): 10m wind velocity vector.
- `wind_gusts_10m` (km/h): Peak turbulent wind gust speed.
- `direct_radiation` ($\text{W/m}^2$): Direct beam solar irradiance driving photochemical reactions.
- `cloud_cover` (%): Total column cloud fraction.
- `precipitation` (mm): Hourly rain accumulation.

### Atmospheric Chemistry (Copernicus CAMS)
- `pm2_5` ($\mu\text{g/m}^3$): Fine inhalable particulate matter ($\le 2.5\,\mu\text{m}$).
- `pm10` ($\mu\text{g/m}^3$): Coarse dust and particulate matter ($\le 10\,\mu\text{m}$).
- `nitrogen_dioxide` ($\mu\text{g/m}^3$): $NO_2$ vehicular and industrial combustion tracer.
- `sulphur_dioxide` ($\mu\text{g/m}^3$): $SO_2$ thermal power plant and coal tracer.
- `carbon_monoxide` ($\mu\text{g/m}^3$): $CO$ incomplete combustion tracer.
- `ozone` ($\mu\text{g/m}^3$): $O_3$ secondary photochemical smog pollutant.
- `india_naqi` (CPCB Index): Official composite India National Air Quality Index.

### Road Infrastructure (OpenStreetMap Overpass)
- `total_road_segments`: Count of distinct highway ways within 1,200m radius.
- `major_highways_count`: Motorways, trunk corridors, and primary highways.
- `secondary_roads_count`: Secondary arterials and tertiary collector streets.
- `road_density_per_sqkm`: Calculated linear network density per $\text{km}^2$.
