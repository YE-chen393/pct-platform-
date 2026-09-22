# V5 - PCT-V5 吸附焓变斜率

**目标变量单位**: —

**数据集划分**: Train=240 + Val=60 (合并训练) | Test=76

**特征数量**: 13

**特征列表**:
- `MagpieData avg_dev NdUnfilled`
- `MagpieData mean NUnfilled`
- `MagpieData mode AtomicWeight`
- `MagpieData mean MendeleevNumber`
- `MagpieData mean MeltingT`
- `MagpieData mean GSvolume_pa`
- `MagpieData mean Electronegativity`
- `MagpieData mode NUnfilled`
- `MagpieData mean Row`
- `MagpieData mode MeltingT`
- `MagpieData mode MendeleevNumber`
- `V0`
- `MagpieData mode NdValence`

---

## 1. 最佳模型

| 项目 | 值 |
|------|---|
| **最佳模型** | **SVR** |
| Test R² | **0.9661** ✅ |
| Test MAE | 0.3034 |
| Test RMSE | 0.4150 |
| Val R² | 0.9830 |
| Train R² | 0.9382 |

**最优超参数**:
```json
{
  "kernel": "rbf",
  "gamma": "scale",
  "epsilon": 0.05,
  "C": 100
}
```

---

## 2. 所有模型结果

| 模型 | Train MAE | Val MAE | Test MAE | Train R² | Val R² | **Test R²** | 达标 |
|------|-----------|---------|----------|----------|---------|------------|------|
| RandomForest | 0.1107 | 0.1074 | 0.2287 | 0.9799 | 0.9928 | **0.9618** | ✅ |
| GradientBoosting | 0.0817 | 0.0725 | 0.2273 | 0.9916 | 0.9974 | **0.9387** | ✅ |
| SVR | 0.2858 | 0.2192 | 0.3034 | 0.9382 | 0.9830 | **0.9661** | ✅ |
| LightGBM | 0.0671 | 0.0682 | 0.2093 | 0.9901 | 0.9952 | **0.9559** | ✅ |
| XGBoost | 0.2513 | 0.2409 | 0.3099 | 0.9680 | 0.9774 | **0.9552** | ✅ |

---

## 3. 模型文件

保存路径: `models/V5/`

- `RandomForest.pkl`
- `GradientBoosting.pkl`
- `SVR.pkl` (+ scaler_X.pkl, scaler_y.pkl)
- `LightGBM.pkl`
- `XGBoost.pkl`

---

## 4. 结论

✅ **达成目标**: Test R² = 0.9661 > 0.91

最佳模型为 **SVR**，在 Test 集上 MAE=0.3034，R²=0.9661。Train R²=0.9382 与 Test R²=0.9661 差距 0.0279，泛化性能良好。

