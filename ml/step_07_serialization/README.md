# Step 07: Production Serialization & Real-Time Live Validator

## 1. Objective & Scope
Step 07 packages the trained machine learning pipeline into a production artifact and validates it against live, incoming real-world data:
1. **Pipeline Exporter ([`exporter.py`](file:///d:/college_dev/ml/step_07_serialization/exporter.py)):** Packages the trained champion model, exact 42-feature schema registry, and official CPCB breakpoints into an immutable bundle: [`data/models/pipeline_model.joblib`](file:///d:/college_dev/ml/data/models/pipeline_model.joblib).
2. **Inference Engine ([`inference_engine.py`](file:///d:/college_dev/ml/step_07_serialization/inference_engine.py)):** Provides high-performance single-point and batch inference (`predict_single()` and `predict_batch()`), calculating CPCB health categories, color codes, dynamic confidence intervals ($\pm 22.61$ MAE margin), and standard-weighted dominant pollutant indicators.
3. **Real-Time Live Validator ([`realtime_validator.py`](file:///d:/college_dev/ml/step_07_serialization/realtime_validator.py)):** Fetches instantaneous live telemetry across Vidarbha (ECMWF weather + Copernicus CAMS chemistry), executes inference, and benchmarks predictions side-by-side against active CPCB physical stations.

---

## 2. Production Artifact Details

- **File Path:** [`data/models/pipeline_model.joblib`](file:///d:/college_dev/ml/data/models/pipeline_model.joblib)
- **Metadata Path:** [`data/models/pipeline_metadata.json`](file:///d:/college_dev/ml/data/models/pipeline_metadata.json)
- **Model Architecture:** LightGBM Champion Regressor (`LGBMRegressor`, best tree iteration 529)
- **Input Features Required:** Exactly 42 features matching the split metadata schema (pruned static distance proxies, dynamic dispersion vectors preserved)
- **Target Output:** Continuous Indian National Air Quality Index (`india_naqi`, 0.0 to 500.0)
- **Test Metrics:** $R^2 = 0.5765$, MAE = $22.61$ AQI points, Pearson $r = 0.7638$

---

## 3. Execution Commands

```bash
# 1. Package and export production pipeline bundle
python ml/step_07_serialization/exporter.py

# 2. Run real-time validation against live operational telemetry & CPCB ground truth
python ml/step_07_serialization/realtime_validator.py
```
- **Outputs:**
  - `data/models/pipeline_model.joblib`
  - `data/models/pipeline_metadata.json`
  - `data/validation/realtime_validation_report.json`

