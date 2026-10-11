# Step 04: Spatial & Temporal Data Splitting

## 1. Objective & Scope
Standard random k-fold cross-validation suffers from **temporal and spatial autocorrelation leakage** (evaluating on timestamps identical to training data).  

Step 04 implements **leakage-free chronological and spatial holdouts** across all 4 authentic CPCB physical monitoring stations in Vidarbha:
- **`NAGPUR_CENTRAL`**: 7,174 hourly records
- **`CHANDRAPUR_MIDC`**: 6,740 hourly records
- **`AMRAVATI_CENTRAL`**: 7,090 hourly records
- **`AKOLA_WEST`**: 7,066 hourly records
- **Total Dataset**: 28,070 continuous records

---

## 2. Feature Schema & Target Definition
- **Target Label ($y$):** `india_naqi` — Physical continuous analyzer readings recorded by official CPCB/MPCB CAAQMS nodes.
- **Input Features ($X$):** 50 predictive features, including:
  - `cams_satellite_naqi` (Copernicus CAMS atmospheric chemistry model estimate)
  - Atmospheric tracers: `pm2_5`, `pm10`, `nitrogen_dioxide`, `sulphur_dioxide`, `carbon_monoxide`, `ozone`, `combustion_tracer_ratio`
  - Thermodynamics & Meteorology: `temperature_2m`, `relative_humidity_2m`, `dew_point_spread`, `wind_u`, `wind_v`, etc.
  - Cyclic temporal encodings: $\sin/\cos$ for hour, day of week, and month
  - OpenStreetMap road infrastructure metrics: `osm_total_roads`, `osm_major_highways`, `osm_road_density_km2`
  - Spatial transport physics: Geodesic Haversine distances, IDW weights, wind alignment bearings, and downwind dispersion factors

---

## 3. Split Protocol

### A. Chronological Partition (Temporal Holdout)
| Split Partition | Time Period (2025) | Rows | Percentage | Meteorological Context |
| :--- | :--- | :--- | :--- | :--- |
| **Train Set** | Feb 19 – Sep 30, 2025 | 20,024 | 71.3% | Spring, Summer & Monsoon seasons |
| **Validation Set** | Oct 01 – Nov 15, 2025 | 3,984 | 14.2% | Post-monsoon transition & tuning |
| **Test Set** | Nov 16 – Dec 31, 2025 | 4,062 | 14.5% | Severe winter peak inversion & fog episode |

### B. Leave-One-Station-Out (LOSO) Spatial Transfer Benchmark
For each of the 4 stations:
- Train the model on the **3 other stations** (~21,000 rows)
- Evaluate zero-shot virtual estimation on the **held-out 4th station** (~7,000 rows)
This directly measures the model's accuracy when deployed at a location with zero physical sensors!

---

## 4. Execution Command

```bash
python ml/step_04_data_split/splitter.py
```

### Generated Artifacts (`data/split/`)
- `X_train.csv`, `y_train.csv` (20,024 rows $\times$ 50 features)
- `X_val.csv`, `y_val.csv` (3,984 rows $\times$ 50 features)
- `X_test.csv`, `y_test.csv` (4,062 rows $\times$ 50 features)
- `train_matrix.csv`, `val_matrix.csv`, `test_matrix.csv` (complete feature + metadata matrices)
- `loso_spatial_splits/` (4 cross-station holdout pairs)
- `split_metadata.json` (comprehensive split registry and feature names)
