# Clean Data Store: Pan-India HCHO & Biomass Burning Surveillance

This directory houses the structured, analysis-ready datasets for the **Pan-India Satellite Formaldehyde (HCHO) and Biomass Burning Analysis System**.

The repository has been restructured by **relevance in a nested hierarchy**, purging redundant/obsolete files (reducing footprint from ~90 MB to ~6.4 MB) and grouping files logically according to their role in the visualization dashboard and analytical pipeline.

---

## Directory Hierarchy (Sorted by Relevance)

```
ds/data/
│
├── final_map_data/                      ← [Tier 1] Final visual layers rendered directly on the Leaflet map
│   ├── india_hcho_aligned.geojson       (Continuous Sentinel-5P HCHO column 0.25° mesh)
│   ├── active_fires_india_processed.geojson (NASA VIIRS/MODIS fire detections with FRP)
│   ├── wind_transport_vectors.geojson   (ECMWF ERA5 synoptic 10m wind transport vectors)
│   ├── hcho_hotspots_getis_ord.geojson  (Getis-Ord Gi* statistical hotspot classifications)
│   └── biomass_clusters_dbscan.geojson  (DBSCAN delineated biomass burning plume polygons)
│
├── evaluation_and_correlations/         ← [Tier 2] Statistical models, peer-review metrics & KPIs
│   ├── hotspots_summary.json            (Master summary KPIs, DBSCAN metrics, cluster ranking)
│   ├── correlation_report.json          (OLS bivariate regressions, Pearson r, Spearman rho, wind transport)
│   └── regional_correlations.csv        (7 agro-ecological zones statistical breakdown)
│
├── processed_grid/                      ← [Tier 3] Harmonized master analytical table
│   └── india_hcho_preprocessed_grid.csv (Unified 0.25° x 0.25° table: S5P HCHO + VIIRS + ERA5)
│
└── raw/                                 ← [Tier 4] Telemetry & sensor ingestions sorted by source
    ├── satellite_hcho/
    │   ├── S5P_OFFL_L2__HCHO_India_biomass.nc (Cropped Sentinel-5P TROPOMI NetCDF-4)
    │   └── S5P_HCHO_India_points.csv          (Extracted HCHO observation points table)
    ├── active_fires/
    │   └── VIIRS_MODIS_India_Active_Fires_Raw.csv (Master unified raw fire catalog across India)
    ├── meteorology_era5/
    │   ├── ERA5_reanalysis_met_India.csv      (Hourly synoptic meteorological corridor records)
    │   └── ERA5_reanalysis_met_India.nc       (10m wind vector NetCDF-4 grid)
    └── metadata/
        └── ingestion_metadata.json            (Pipeline run metadata and satellite stream log)
```

---

## Detailed Directory Breakdown

### 1. `final_map_data/` (Visual Map Presentation)
*Directly consumed by the frontend Leaflet map on Page 3 of the application via `/api/hcho/*` endpoints.*

| File Name | Format | Size | Description & Role |
| :--- | :--- | :--- | :--- |
| **`india_hcho_aligned.geojson`** | GeoJSON Point Collection | ~2.1 MB | High-resolution mesh of Sentinel-5P TROPOMI HCHO tropospheric column densities ($\times 10^{15}\ \text{molec/cm}^2$). Renders the continuous color-ramped atmospheric heatmap across India. |
| **`active_fires_india_processed.geojson`** | GeoJSON Point Collection | ~121 KB | Filtered NASA VIIRS (375m) & MODIS (1km) active fire points with Fire Radiative Power (`frp_mw`), detection confidence, and satellite sensor type. Renders interactive fire markers. |
| **`wind_transport_vectors.geojson`** | GeoJSON LineString | ~325 KB | Synoptic 10m atmospheric wind direction vectors on a regular 1.0° grid derived from ECMWF ERA5 reanalysis. Visualizes plume advection pathways (e.g., northwest transport towards the Bay of Bengal). |
| **`hcho_hotspots_getis_ord.geojson`** | GeoJSON Point Collection | ~951 KB | Spatial clusters of elevated HCHO computed via Getis-Ord $G_i^*$ local spatial statistics. Categorized into 99% ($Z \ge +2.58$), 95% ($Z \ge +1.96$), and 90% ($Z \ge +1.65$) statistical confidence tiers. |
| **`biomass_clusters_dbscan.geojson`** | GeoJSON Polygon Collection | ~54 KB | 58 discrete spatial biomass burning plume boundaries delineated using DBSCAN density clustering with Haversine geodesic distance ($\varepsilon = 35\text{ km}, \text{min\_samples} = 15$). |

---

### 2. `evaluation_and_correlations/` (Analytics & Evaluation)
*Contains scientific evaluation metrics, regression parameters, and dashboard KPI payloads.*

| File Name | Format | Size | Description & Role |
| :--- | :--- | :--- | :--- |
| **`hotspots_summary.json`** | JSON | ~85 KB | Master analytical summary payload returned by `/api/hcho/summary`. Contains total fires ($9,032$), cumulative FRP ($46,962.5\ \text{MW}$), national mean HCHO, DBSCAN clustering metrics (Silhouette score = 0.5302, Davies-Bouldin = 0.391), and cluster rankings. |
| **`correlation_report.json`** | JSON | ~4.5 KB | Comprehensive bivariate regression parameters between biomass burning intensity (FRP) and tropospheric HCHO loadings (Pearson $r$, Spearman $\rho$, OLS slope, $R^2$, and $p$-values). |
| **`regional_correlations.csv`** | CSV | ~747 B | Zonal comparison table aggregating fire intensity, HCHO levels, and correlation coefficients across 7 distinct Indian agro-ecological corridors (Punjab-Haryana, Indo-Gangetic Plain, Vidarbha/Central India, etc.). |

---

### 3. `processed_grid/` (Master Analytical Dataset)
*The unified spatial grid that connects satellite atmospheric chemistry with ground fire observations.*

| File Name | Format | Size | Description & Role |
| :--- | :--- | :--- | :--- |
| **`india_hcho_preprocessed_grid.csv`** | CSV | ~990 KB | Master $0.25^\circ \times 0.25^\circ$ grid (~6,147 cells) created by `02_preprocessing.py`. Merges QA-filtered Sentinel-5P HCHO ($\text{qa\_value} \ge 0.5$), aggregated VIIRS/MODIS fire counts, summed FRP ($\text{MW}$), eco-zone classification, and interpolated ERA5 wind vectors ($u_{10}, v_{10}$). |

---

### 4. `raw/` (Source Telemetry Nested by Sensor)
*Clean, structured telemetry archives. Unprocessed intermediate downloads and obsolete dumps have been purged.*

* **`raw/satellite_hcho/`**:
  * `S5P_OFFL_L2__HCHO_India_biomass.nc` (~157 KB): Authentic Sentinel-5P TROPOMI Level-3 NetCDF-4 cropped strictly to the Indian terrestrial domain ($6.5^\circ\text{N} - 37.0^\circ\text{N}, 68.0^\circ\text{E} - 97.5^\circ\text{E}$).
  * `S5P_HCHO_India_points.csv` (~917 KB): Flattened tabular representation of S5P grid points with QA scores, cloud fractions, and HCHO column densities.
* **`raw/active_fires/`**:
  * `VIIRS_MODIS_India_Active_Fires_Raw.csv` (~1.1 MB): Master unified and deduplicated active thermal detections from Suomi-NPP VIIRS, NOAA-20 VIIRS, and Terra/Aqua MODIS within India.
* **`raw/meteorology_era5/`**:
  * `ERA5_reanalysis_met_India.csv` (~625 KB): Hourly synoptic meteorological records (wind speed, direction, $u_{10}, v_{10}$, temperature, pressure) across 32 key Indian geographic corridors.
  * `ERA5_reanalysis_met_India.nc` (~128 KB): NetCDF-4 spatial grid representation of the ERA5 10m wind fields.
* **`raw/metadata/`**:
  * `ingestion_metadata.json` (~464 B): Execution logs tracking observation dates, satellite stream type (`OFFL`/`NRTI`), timestamps, and total detections.

---

## Data Pipeline Integration

```
[01_data_ingestion.py]
         │
         ▼
     raw/ (satellite_hcho, active_fires, meteorology_era5)
         │
         ▼
[02_preprocessing.py]
         │
         ├──► processed_grid/india_hcho_preprocessed_grid.csv
         │
         └──► final_map_data/ (india_hcho_aligned.geojson, active_fires_india_processed.geojson)
                 │
                 ▼
[03_hotspot_generation.py]
         │
         ├──► final_map_data/ (hcho_hotspots_getis_ord.geojson, biomass_clusters_dbscan.geojson)
         │
         └──► evaluation_and_correlations/hotspots_summary.json
                 │
                 ▼
[04_correlation_analysis.py]
         │
         ├──► final_map_data/wind_transport_vectors.geojson
         │
         └──► evaluation_and_correlations/ (correlation_report.json, regional_correlations.csv)
```
