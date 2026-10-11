# Step 02: Preprocessing & Physical Feature Engineering

## 1. Objective & Scope
Step 02 takes the authentic raw datasets (`data/raw/weather/` and `data/raw/air_quality/`) and applies rigorous, data-driven preprocessing:
1. Resolves time-series data quality issues (temporal alignment, frequency verification, sensor dropouts).
2. Derives atmospheric physical vectors and thermodynamics.
3. Formulates continuous trigonometric cyclic temporal encodings.
4. Computes empirical chemical combustion tracer interactions.
5. Computes official CPCB India National AQI (NAQI) composite targets.

**Storage Output:** Clean datasets saved to [`data/clean/weather_clean.csv`](file:///d:/college_dev/ml/data/clean/weather_clean.csv) and [`data/clean/air_quality_clean.csv`](file:///d:/college_dev/ml/data/clean/air_quality_clean.csv).

---

## 2. Step-by-Step Preprocessing Protocol

### Step 2.1: Temporal Alignment & Sorting
- Parse timestamps into ISO 8601 datetimes.
- Group by `station_id` and sort strictly by ascending timestamp to guarantee time-series continuity.
- Ensure unified hourly resolution across all 4 stations.

### Step 2.2: Missing Value & Dropout Imputation
- Real-world atmospheric sensors occasionally encounter brief transmission drops.
- To prevent artificial variance without introducing synthetic noise:
  - Perform **linear time-series interpolation** (`interpolate(method='linear')`) bounded within each station's timeline.
  - Apply backward and forward boundary fills (`bfill().ffill()`) for edge dropouts.
  - Zero synthetic mean-replacement is used.

### Step 2.3: Atmospheric Thermodynamics & Vector Decomposition
Raw scalar weather observations are converted into physical transport vectors:
1. **Dew Point Spread:**
   $$\text{DewPointSpread} = \max(0.0, T_{2m} - T_{dew})$$
   Measures atmospheric moisture deficit; lower spread indicates fog/smog condensation conditions.
2. **Horizontal Wind Vector Decomposition:**
   Convert scalar speed ($w_s$) and compass direction ($\theta$) into orthogonal Eulerian velocity components:
   $$u = -w_s \cdot \sin(\text{radians}(\theta)) \quad \text{(Zonal West-to-East component)}$$
   $$v = -w_s \cdot \cos(\text{radians}(\theta)) \quad \text{(Meridional South-to-North component)}$$

### Step 2.4: Cyclic Trigonometric Temporal Encodings
Time is continuous and cyclical (hour 23 is 1 hour away from hour 0; December is 1 month away from January). Linear integer representations create artificial step discontinuities.
We encode temporal variables onto continuous unit circles:
- **Diurnal (24-Hour Cycle):**
  $$\sin\_hour = \sin\left(\frac{2\pi \cdot \text{hour}}{24}\right), \quad \cos\_hour = \cos\left(\frac{2\pi \cdot \text{hour}}{24}\right)$$
- **Weekly (7-Day Cycle):**
  $$\sin\_dow = \sin\left(\frac{2\pi \cdot \text{dow}}{7}\right), \quad \cos\_dow = \cos\left(\frac{2\pi \cdot \text{dow}}{7}\right)$$
- **Seasonal (12-Month Annual Cycle):**
  $$\sin\_month = \sin\left(\frac{2\pi \cdot \text{month}}{12}\right), \quad \cos\_month = \cos\left(\frac{2\pi \cdot \text{month}}{12}\right)$$
- **Weekend Binary Indicator:** `is_weekend = 1` if `dow >= 5`, else `0`.

### Step 2.5: Chemical Combustion Tracer Ratio
Measures whether atmospheric pollution is dominated by fresh vehicular/industrial fossil fuel combustion ($NO_2$) versus smoldering biomass/open waste burning ($CO$):
$$\text{combustion\_tracer\_ratio} = \frac{NO_2}{CO + 10^{-4}}$$

### Step 2.6: Official CPCB India NAQI Composite Target
Computes the true ground truth target according to official Indian National Ambient Air Quality Standards (NAAQS):
$$\text{NAQI} = \max(\text{SubIndex}_{\text{PM2.5}}, \text{SubIndex}_{\text{PM10}}, \text{SubIndex}_{\text{NO2}}, \text{SubIndex}_{\text{SO2}}, \text{SubIndex}_{\text{CO}}, \text{SubIndex}_{\text{O3}})$$
Each sub-index is calculated via piecewise linear interpolation over official CPCB concentration breakpoints.

---

## 3. Running Preprocessing

```bash
python ml/step_02_preprocessing/cleaner.py
```
- **Inputs:** `data/raw/weather/weather_vidarbha_combined.csv`, `data/raw/air_quality/air_quality_vidarbha_combined.csv`
- **Outputs:**
  - `data/clean/weather_clean.csv` (35,040 rows $\times$ 19 columns)
  - `data/clean/air_quality_clean.csv` (35,040 rows $\times$ 18 columns)
