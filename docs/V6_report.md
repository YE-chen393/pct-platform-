# V6 - V6 吸附焓变截距

**目标变量单位**: —

**数据集划分**: Train=259 + Val=56 (合并训练) | Test=56

**特征数量**: 18

**特征列表**:
- `MagpieData avg_dev Column`
- `MagpieData minimum MeltingT`
- `MagpieData avg_dev NdValence`
- `MagpieData avg_dev NsValence`
- `MagpieData maximum MendeleevNumber`
- `MagpieData mean MendeleevNumber`
- `MagpieData mean NUnfilled`
- `MagpieData mean SpaceGroupNumber`
- `MagpieData minimum NUnfilled`
- `MagpieData avg_dev GSmagmom`
- `MagpieData avg_dev NdUnfilled`
- `MagpieData avg_dev SpaceGroupNumber`
- `MagpieData maximum MeltingT`
- `MagpieData mean MeltingT`
- `MagpieData mean Number`
- `MagpieData minimum NValence`
- `MagpieData mode NValence`
- `V0`

---

## 1. 最佳模型

| 项目 | 值 |
|------|---|
| **最佳模型** | **LightGBM** |
| Test R² | **0.9322** ✅ |
| Test MAE | 0.2348 |
| Test RMSE | 0.5666 |
| Val R² | 0.9961 |
| Train R² | 0.9929 |

**最优超参数**:
```json
{
  "subsample": 1.0,
  "reg_lambda": 1.0,
  "reg_alpha": 0,
  "num_leaves": 31,
  "n_estimators": 500,
  "max_depth": 7,
  "learning_rate": 0.1,
  "colsample_bytree": 0.8
}
```

---

## 2. 所有模型结果

| 模型 | Train MAE | Val MAE | Test MAE | Train R² | Val R² | **Test R²** | 达标 |
|------|-----------|---------|----------|----------|---------|------------|------|
| RandomForest | 0.2259 | 0.1582 | 0.4362 | 0.9816 | 0.9903 | **0.8961** | ❌ |
| GradientBoosting | 0.1125 | 0.0770 | 0.2645 | 0.9919 | 0.9955 | **0.9246** | ✅ |
| SVR | 0.4832 | 0.3207 | 0.7618 | 0.8999 | 0.9652 | **0.7248** | ❌ |
| LightGBM | 0.0824 | 0.0622 | 0.2348 | 0.9929 | 0.9961 | **0.9322** | ✅ |
| XGBoost | 0.3188 | 0.2168 | 0.4788 | 0.9712 | 0.9858 | **0.8829** | ❌ |

---

## 3. 模型文件

保存路径: `models/V6/`

- `RandomForest.pkl`
- `GradientBoosting.pkl`
- `SVR.pkl` (+ scaler_X.pkl, scaler_y.pkl)
- `LightGBM.pkl`
- `XGBoost.pkl`

---

## 4. 结论

✅ **达成目标**: Test R² = 0.9322 > 0.91

最佳模型为 **LightGBM**，在 Test 集上 MAE=0.2348，R²=0.9322。Train R²=0.9929 与 Test R²=0.9322 差距 0.0608，泛化性能可接受。

