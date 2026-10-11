# Step 03: Feature Merging & Spatial Dispersion Physics

## 1. Objective & Scope
Step 03 brings together all authentic data streams into a single, unified analytical matrix:
1. **Compound Index Merge:** Joins clean weather and air quality time-series on `[timestamp, station_id]`.
2. **Infrastructure Integration:** Attaches authentic OpenStreetMap (OSM) road network metrics.
3. **Spatial Physics Engine ([`spatial_physics.py`](file:///d:/college_dev/ml/step_03_feature_merge/spatial_physics.py)):** Calculates geodesic distances, inverse-distance weights (IDW), wind transport vector alignments, and downwind dispersion factors to all 4 Vidarbha reference nodes.

**Storage Output:** [`data/clean/master_analytical_matrix.csv`](file:///d:/college_dev/ml/data/clean/master_analytical_matrix.csv) (35,040 rows $\times$ 49 feature columns).

---

## 2. Spatial Physics & Dispersion Transport Formulations

To allow the machine learning model to estimate air quality at any arbitrary geographic coordinate across Vidarbha (including unmonitored rural and semi-urban locations), the spatial physics engine computes physics-informed geographic relationships relative to the 4 reference anchor stations:
- **Nagpur Central** ($21.1458^\circ\text{N}, 79.0882^\circ\text{E}$)
- **Chandrapur MIDC** ($19.9615^\circ\text{N}, 79.2961^\circ\text{E}$)
- **Amravati Central** ($20.9374^\circ\text{N}, 77.7796^\circ\text{E}$)
- **Akola West** ($20.7002^\circ\text{N}, 77.0082^\circ\text{E}$)

### A. Geodesic Haversine Distance ($d_i$)
Calculates true spherical surface distance from coordinate $(lat, lon)$ to reference station $(lat_i, lon_i)$:
$$a = \sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)$$
$$d_i = 2 R \cdot \arctan2(\sqrt{a}, \sqrt{1 - a}), \quad R = 6371.0\,\text{km}$$

### B. Inverse Distance Weighting ($IDW_i$)
Models natural spatial decay of localized emissions:
$$IDW_i = \frac{1}{\max(d_i, 1.0)^2}$$

### C. Bearing Azimuth ($\theta_{\text{azimuth}, i}$)
Calculates the geographic bearing from reference station $i$ toward coordinate $(lat, lon)$:
$$\theta_{\text{azimuth}, i} = \arctan2(\sin(\Delta \lambda)\cos(\phi_2), \cos(\phi_1)\sin(\phi_2) - \sin(\phi_1)\cos(\phi_2)\cos(\Delta \lambda)) \pmod{360^\circ}$$

### D. Wind Transport Alignment ($\cos(\Delta \theta)$)
Determines whether ambient wind is transporting pollution plume directly toward the target location ($+1.0$), blowing crosswind ($0.0$), or blowing away from it ($-1.0$):
$$\text{alignment}_i = \cos(\text{radians}(\theta_{\text{wind}} - \theta_{\text{azimuth}, i}))$$

### E. Downwind Dispersion Factor
Combines wind velocity with directional alignment:
$$\text{dispersion}_i = w_s \cdot \text{alignment}_i \quad (\text{in km/h})$$

---

## 3. The Complete 49-Feature Analytical Registry

The resulting master dataset contains 49 fully analytical, authentic features:

| Category | Count | Features |
| :--- | :--- | :--- |
| **Meteorology** | 10 | `temperature_2m`, `relative_humidity_2m`, `dew_point_2m`, `surface_pressure`, `wind_speed_10m`, `wind_direction_10m`, `wind_gusts_10m`, `precipitation`, `cloud_cover`, `direct_radiation` |
| **Physical Derivatives** | 3 | `dew_point_spread`, `wind_u`, `wind_v` |
| **Cyclic Time Encodings** | 7 | `sin_hour`, `cos_hour`, `sin_dayofweek`, `cos_dayofweek`, `sin_month`, `cos_month`, `is_weekend` |
| **Chemical Tracers** | 7 | `pm2_5`, `pm10`, `nitrogen_dioxide`, `sulphur_dioxide`, `carbon_monoxide`, `ozone`, `combustion_tracer_ratio` |
| **GIS Infrastructure (OSM)** | 4 | `osm_total_roads`, `osm_major_highways`, `osm_secondary_roads`, `osm_road_density_km2` |
| **Geographic Coordinates** | 2 | `latitude`, `longitude` |
| **Spatial Distance (km)** | 4 | `dist_to_nagpur_central_km`, `dist_to_chandrapur_midc_km`, `dist_to_amravati_central_km`, `dist_to_akola_west_km` |
| **Spatial IDW Weights** | 4 | `idw_weight_nagpur_central`, `idw_weight_chandrapur_midc`, `idw_weight_amravati_central`, `idw_weight_akola_west` |
| **Wind Alignment Vectors** | 4 | `wind_alignment_nagpur_central`, `wind_alignment_chandrapur_midc`, `wind_alignment_amravati_central`, `wind_alignment_akola_west` |
| **Downwind Dispersion** | 4 | `downwind_dispersion_nagpur_central`, `downwind_dispersion_chandrapur_midc`, `downwind_dispersion_amravati_central`, `downwind_dispersion_akola_west` |
| **Target Label** | 1 | `india_naqi` (Official CPCB India NAQI Composite) |

---

## 4. Execution Command

```bash
python ml/step_03_feature_merge/merger.py
```
Outputs the complete master analytical training matrix:
- **Path:** [`data/clean/master_analytical_matrix.csv`](file:///d:/college_dev/ml/data/clean/master_analytical_matrix.csv)
- **Rows:** 35,040 rows (100% complete, zero missing values)
- **Columns:** 49 features + 1 target
