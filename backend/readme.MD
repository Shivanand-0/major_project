Here is the complete step-by-step breakdown of what happens internally from the moment you click on the map or search for a location to the final calculated Air Quality Index (AQI) displayed on screen.

 *

### Step 1: User Action & Frontend Trigger (Browser)

1. User Interaction:Map Click: When you tap anywhere on the Leaflet map, Leaflet captures the click coordinates [lat, lon] (e.g., 20.9374° N, 77.7796° E).Search Input: When you type a query (e.g. "RBU", "Amravati Camp", or raw coordinates 20.9374, 77.7796) and click Check Air Quality, [app.js](file:///d:/college_dev/backend/static/app.js) parses the text, resolves the corresponding coordinates, and centers the map.
2. Immediate UI Feedback:The map pin moves instantly to the selected point with a pulsing ring.The Real-Time Reading panel immediately activates a loading spinner overlay (setReadingCardLoading(true)), hiding any stale previous data so you never see old readings while new data is being evaluated.A unique request tracking ID (currentEvaluationId) is incremented to prevent race conditions if you click multiple points in rapid succession.

 *

### Step 2: Client-Side Routing & Caching Decision

In \[app.js\](file:///d:/college\_dev/backend/static/app.js) (`selectCoordinate`):

*   **Is it a pre-loaded city station?** (Nagpur, Chandrapur, Amravati, Akola):  
    If the location was already fetched during initial page load via `/api/nodes`, the browser immediately uses the existing cached node payload (`cachedNode`), resolving in near **0 ms**.
*   **Is it an arbitrary/custom point on the map?**:  
    `cachedNode` is `null`. The browser makes an asynchronous HTTP call:
    
    ```http
    POST /api/predict
    Content-Type: application/json
    { "latitude": 20.9374, "longitude": 77.7796 }
    ```
    

 *

### Step 3: Backend Ingestion of Real-Time Atmospheric Telemetry

The FastAPI backend (\[backend/main.py\](file:///d:/college\_dev/backend/main.py)) receives the coordinates and calls the `VirtualSensorEstimator` service (\[backend/services/estimator.py\](file:///d:/college\_dev/backend/services/estimator.py)):

1. Instantaneous Meteorological Query (Open-Meteo / ECMWF):Fetches current real-time weather at that exact latitude and longitude:2-meter Temperature (∘C), Relative Humidity (%), Dew Point (∘C)Surface Atmospheric Pressure (hPa)Wind Speed (10m, km/h), Wind Direction (0–360∘), Wind GustsDirect Solar Radiation (W/m2), Cloud Cover (%), Precipitation
2. Chemical Tracers & Satellite Sensors (Copernicus CAMS):Fetches current atmospheric pollutant column tracer concentrations:Surface Particulate Matter (PM2.5​ and PM10​ in μg/m3)Nitrogen Dioxide (NO2​), Sulphur Dioxide (SO2​)Ground-level Ozone (O3​), Carbon Monoxide (CO)
3. OpenStreetMap (OSM) Road Network Density:Queries the local GIS road topology ([osm_road_network.json](file:///d:/college_dev/backend/models/osm_road_network.json)) to determine:Total road segments, major highways (motorways/trunks), secondary roads, and road density per km2 around that point.

 *

### Step 4: The 42-Feature Vector Construction

The backend builds the exact **42-dimensional numerical feature vector** that the machine learning model was trained on:

| Feature Category | Features Included | Physical Role / Significance |
| :--- | :--- | :--- |
| **1\. Instantaneous Meteorology (10)** | `temperature_2m`, `relative_humidity_2m`, `dew_point_2m`, `surface_pressure`, `wind_speed_10m`, `wind_direction_10m`, `wind_gusts_10m`, `precipitation`, `cloud_cover`, `direct_radiation` | Atmospheric boundary layer height, convection, and air density. |
| **2\. Thermodynamics & Vector Wind (3)** | `dew_point_spread` ($T - T_{\text{dew}}$), `wind_u` (zonal), `wind_v` (meridional) | Fog/haze formation potential; horizontal transport vector components. |
| **3\. Chemical Tracers & Satellites (8)** | `pm2_5`, `pm10`, `nitrogen_dioxide`, `sulphur_dioxide`, `ozone`, `carbon_monoxide`, `cams_satellite_naqi`, `combustion_tracer_ratio` ($\text{NO}_2 / \text{CO}$) | Background chemical burden, photochemical aging, and vehicular vs biomass combustion ratios. |
| **4\. Cyclical Temporal Encodings (7)** | `sin_hour`, `cos_hour`, `sin_dayofweek`, `cos_dayofweek`, `sin_month`, `cos_month`, `is_weekend` | Captures diurnal traffic peaks (morning/evening rush hour), weekly industrial cycles, and winter boundary layer inversions vs summer monsoon scavenging. |
| **5\. Urban Infrastructure (4)** | `osm_total_roads`, `osm_major_highways`, `osm_secondary_roads`, `osm_road_density_km2` | Local vehicular emissions and traffic volume proxy without requiring physical vehicle counters. |
| **6\. Downwind Physics to Regional Hubs (10)** | `dist_to_*`, `idw_weight_*`, `wind_alignment_*` ($\cos(\theta_{\text{wind}} - \theta_{\text{azimuth}})$), `downwind_dispersion_*` | Quantifies whether the selected point is directly downwind of major industrial corridors (e.g. Chandrapur thermal power/coal belt or Nagpur urban basin). |

 *

### Step 5: Machine Learning Inference (LightGBM Champion)

The feature vector is passed to the serialized model pipeline (\[pipeline\_model.joblib\](file:///d:/college\_dev/backend/models/pipeline\_model.joblib)):

1. LightGBM Regressor:The champion model is a tuned LightGBM Regressor (LGBMRegressor, test R2=0.5765, MAE=22.61 AQI points).
2. Raw Model Output:

$$
\text{raw\_prediction} = \text{Model.predict}(X_{42})
$$

3. CPCB NAQI Physical Clipping:The prediction is constrained to the official Indian National Air Quality Index range:

$$
\text{Final AQI} = \text{round}\Big(\min\big(500.0, \max(0.0, \text{raw\_prediction})\big), 1\Big)
$$

4. Confidence Interval:Calculated using the model’s validated error margin buffer:

$$
\text{Confidence Range} = [\text{AQI} - 22.6, \; \text{AQI} + 22.6]
$$

5. Dominant Pollutant Determination:Identifies which pollutant is driving the elevated index (typically PM2.5​ or Dust & PM10​).

 *

### Step 6: CPCB Ground-Truth Validation & Residual Check

*   If your click is within **500 meters of a physical CPCB continuous ambient air monitoring station (CAAQMS)** (such as Civil Lines Nagpur or Chandrapur MIDC):
    *   The system queries the live CPCB portal feed (\[services/cpcb\_ground\_truth.py\](file:///d:/college\_dev/backend/services/cpcb\_ground\_truth.py)).
    *   Calculates the **residual error**:

$$
\text{Residual} = \text{AI Predicted AQI} - \text{Physical Monitor AQI}
$$

*   The card displays both the AI reading and the physical station ground truth side-by-side.
*   If it is an unmonitored location (e.g., Amravati Camp or a rural area):
    *   The system tags it as:  
        *“Autonomous AI Virtual Sensor Node — Unmonitored Coordinate (Instantaneous ML Spatiotemporal Estimation)”*.

 *

### Step 7: Response Delivery & UI Rendering

The backend returns the JSON response in $\approx 200–350\text{ ms}$:

1. Hero Display:The loading spinner vanishes (setReadingCardLoading(false)).The large AQI number (e.g. 159) renders in the CPCB category color:0–50: Good (Green)51–100: Satisfactory (Emerald)101–200: Moderate (Amber/Yellow)201–300: Poor (Orange)301–400: Very Poor (Red)401–500: Severe (Dark Red)
2. Health Advisory:Automatically renders specific activity advice (e.g., “Sensitive groups should reduce prolonged exertion”).
3. Sub-Metrics:Temperature, Humidity, and Main Pollutant (μg/m3) are populated from the live telemetry.
4. Map Popup Pin:The popup re-renders with the final resolved AQI badge and advisory.

 *

### Is Caching Used?

| Level | Caching Behavior | Why? |
| :--- | :--- | :--- |
| **Arbitrary Coordinates (Map Clicks / Custom Search)** | **NO CACHE (Live on Demand)** | Every time you click a new coordinate on the map, it makes a **fresh live query** to Open-Meteo & Copernicus CAMS. This ensures zero fallback to old/stale data. |
| **Pre-Configured City Hubs (`/api/nodes`)** | **YES (180-second TTL)** | The backend caches the 4 main Vidarbha stations (Nagpur, Chandrapur, Amravati, Akola) in memory for **3 minutes** (`_cache_ttl = 180s`) to prevent rate-limiting from rapid page reloads while maintaining near-real-time accuracy. |
| **Static Assets (JavaScript & CSS)** | **NO BROWSER CACHE (`no-store`)** | Configured with `Cache-Control: no-cache, no-store, must-revalidate` so that frontend UI updates, loaders, and fixes load immediately without browser cache issues. |