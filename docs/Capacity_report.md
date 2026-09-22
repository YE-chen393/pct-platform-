# Capacity - Capacity 最大吸附量

**目标变量单位**: mol/kg

**数据集划分**: Train=262 + Val=57 (合并训练) | Test=57

**特征数量**: 16

**特征列表**:
- `MagpieData avg_dev Column`
- `MagpieData avg_dev CovalentRadius`
- `MagpieData avg_dev GSvolume_pa`
- `MagpieData avg_dev MeltingT`
- `MagpieData avg_dev NValence`
- `MagpieData avg_dev NdUnfilled`
- `MagpieData avg_dev SpaceGroupNumber`
- `MagpieData maximum NValence`
- `MagpieData mean Column`
- `MagpieData mean GSvolume_pa`
- `MagpieData mean MeltingT`
- `MagpieData mean MendeleevNumber`
- `MagpieData mode Column`
- `MagpieData mode MendeleevNumber`
- `MagpieData range Electronegativity`
- `V0`

---

## 1. 最佳模型

| 项目 | 值 |
|------|---|
| **最佳模型** | **RandomForest** |
| Test R² | **0.9771** ✅ |
| Test MAE | 0.1012 |
| Test RMSE | 0.2049 |
| Val R² | 0.9917 |
| Train R² | 0.9916 |

**最优超参数**:
```json
{
  "n_estimators": 200,
  "min_samples_split": 4,
  "min_samples_leaf": 2,
  "max_features": 0.33,
  "max_depth": 30
}
```

---

## 2. 所有模型结果

| 模型 | Train MAE | Val MAE | Test MAE | Train R² | Val R² | **Test R²** | 达标 |
|------|-----------|---------|----------|----------|---------|------------|------|
| RandomForest | 0.0666 | 0.0610 | 0.1012 | 0.9916 | 0.9917 | **0.9771** | ✅ |
| GradientBoosting | 0.0522 | 0.0510 | 0.0953 | 0.9930 | 0.9916 | **0.9701** | ✅ |
| SVR | 0.0889 | 0.1055 | 0.1360 | 0.9893 | 0.9778 | **0.9520** | ✅ |
| LightGBM | 0.0472 | 0.0414 | 0.0879 | 0.9934 | 0.9911 | **0.9708** | ✅ |
| XGBoost | 0.1461 | 0.1472 | 0.1649 | 0.9851 | 0.9800 | **0.9659** | ✅ |

---

## 3. 模型文件

保存路径: `models/Capacity/`

- `RandomForest.pkl`
- `GradientBoosting.pkl`
- `SVR.pkl` (+ scaler_X.pkl, scaler_y.pkl)
- `LightGBM.pkl`
- `XGBoost.pkl`
 
---

## 4. 结论

✅ **达成目标**: Test R² = 0.9771 > 0.91

最佳模型为 **RandomForest**，在 Test 集上 MAE=0.1012，R²=0.9771。Train R²=0.9916 与 Test R²=0.9771 差距 0.0145，泛化性能良好。

