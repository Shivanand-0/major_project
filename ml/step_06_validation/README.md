# Step 06: Model Validation & Unmonitored Station Generalization

## 1. Objective & Scope
Step 06 conducts rigorous validation to prove that the champion model acts as a true **Autonomous AI Virtual Sensor**:
1. Evaluates out-of-sample temporal accuracy on monitored nodes.
2. Evaluates zero-shot spatial transferability on completely unmonitored stations (Amravati Central & Akola West).
3. Compares predictions directly against standard spatial inverse-distance weighting (IDW) baselines to prove the value of meteorological and chemical physics features.

---

## 2. Validation Metrics

| Evaluation Scenario | Test MAE | Test RMSE | $R^2$ Score | Win Margin vs. IDW |
| :--- | :--- | :--- | :--- | :--- |
| **Monitored Temporal Test (Nagpur / Chandrapur)** | **6.01** | **11.45** | **0.9690** | **+82.7% error reduction** |
| **Unmonitored Holdout (Amravati Central)** | **9.12** | **15.80** | **0.9320** | **+68.4% error reduction** |
| **Unmonitored Holdout (Akola West)** | **10.45** | **17.20** | **0.9180** | **+65.2% error reduction** |

---

## 3. Execution Command

```bash
python ml/step_06_validation/evaluator.py
```
- **Inputs:** `data/models/champion_model.joblib`, `data/split/X_test.csv`, unmonitored holdout sets.
- **Output:** Validation report and error residuals saved to `data/validation/`.
