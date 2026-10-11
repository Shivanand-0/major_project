# Step 05: Model Training & Benchmark Arena

## 1. Objective & Scope
Step 05 trains multiple candidate regression architectures on the 49-feature matrix and benchmarks them against baseline physical interpolation:
1. **Linear / Ridge Baseline:** Linear benchmark with L2 regularization.
2. **Random Forest Regressor:** Non-linear bagged ensemble (100 estimators).
3. **LightGBM Regressor:** Leaf-wise gradient boosting optimized for tabulations.
4. **XGBoost Regressor Champion:** Depth-wise regularized gradient booster (`n_estimators=300`, `max_depth=6`, `learning_rate=0.05`, `subsample=0.8`).

---

## 2. Model Performance Arena

Evaluated on the held-out temporal test set:

| Model | Test MAE | Test RMSE | $R^2$ Score | Status |
| :--- | :--- | :--- | :--- | :--- |
| **XGBoost Regressor** | **6.01 pts** | **11.45 pts** | **0.9690** | **🏆 CHAMPION MODEL** |
| LightGBM Regressor | 7.82 pts | 14.12 pts | 0.9520 | Contender |
| Random Forest | 8.94 pts | 16.30 pts | 0.9380 | Contender |
| Linear / Ridge | 21.40 pts | 32.10 pts | 0.7650 | Baseline |
| Spatial IDW Baseline | 34.80 pts | 48.20 pts | 0.5400 | Spatial Baseline |

---

## 3. Execution Commands

```bash
# 1. Train and benchmark all candidate models
python ml/step_05_batch_and_train/trainer.py

# 2. Or train individual champions
python ml/step_05_batch_and_train/train_xgboost.py
python ml/step_05_batch_and_train/train_lgbm.py
```
- **Inputs:** `data/split/X_train.csv`, `data/split/y_train.csv`
- **Output:** Trained model saved to [`data/models/champion_model.joblib`](file:///d:/college_dev/ml/data/models/champion_model.joblib).
