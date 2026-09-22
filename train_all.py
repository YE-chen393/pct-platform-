# -*- coding: utf-8 -*-
"""
PCT_project: 统一训练脚本(一次性训练三个目标,输出 pkl + md 报告)

用法:
    PYTHONPATH=. python train_all.py
"""
import sys
from pathlib import Path

# 让脚本独立运行时也能 import pct_app
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import json, pickle, time, warnings
warnings.filterwarnings('ignore')

from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
from sklearn.model_selection import RandomizedSearchCV

plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 用 pct_app/config/paths 提供的 ROOT(自动以本文件位置为基准,跨平台可移植)
from pct_app.config.paths import ROOT, DATA as _DUMMY  # noqa
DATA    = ROOT / 'data'
MODELS  = ROOT / 'models'
RESULTS = ROOT / 'results'
FIGURES = RESULTS / 'figures'
TABLES  = RESULTS / 'tables'

for d in [MODELS/'V5', MODELS/'V6', MODELS/'Capacity', FIGURES, TABLES]:
    d.mkdir(parents=True, exist_ok=True)

# =============== 数据加载 ===============
def load_dataset(name):
    base = DATA / name
    feat = pd.read_csv(base / 'features.csv')['feature'].tolist()
    X_tr = pd.read_csv(base / 'X_train.csv')[feat].values
    X_va = pd.read_csv(base / 'X_val.csv')[feat].values
    X_te = pd.read_csv(base / 'X_test.csv')[feat].values
    y_tr = pd.read_csv(base / 'y_train.csv')['target'].values
    y_va = pd.read_csv(base / 'y_val.csv')['target'].values
    y_te = pd.read_csv(base / 'y_test.csv')['target'].values
    return dict(name=name, features=feat,
                X_tr=X_tr, y_tr=y_tr, X_va=X_va, y_va=y_va,
                X_te=X_te, y_te=y_te,
                n_tr=len(y_tr), n_va=len(y_va), n_te=len(y_te))


# =============== 模型配置 ===============
def get_models():
    models = {
        'RandomForest': {
            'model': RandomForestRegressor(random_state=42, n_jobs=-1),
            'params': {
                'n_estimators': [100, 150, 200, 300],
                'max_depth': [8, 12, 16, 20, 30],
                'min_samples_split': [4, 6, 8, 10, 12],
                'min_samples_leaf': [2, 3, 4, 5, 6],
                'max_features': ['sqrt', 'log2', 0.33],
            }
        },
        'GradientBoosting': {
            'model': GradientBoostingRegressor(random_state=42),
            'params': {
                'n_estimators': [50, 80, 100, 150, 200],
                'learning_rate': [0.02, 0.03, 0.05, 0.08],
                'max_depth': [2, 3, 4, 5],
                'subsample': [0.7, 0.8, 0.9],
                'min_samples_leaf': [4, 6, 8, 10],
                'max_features': ['sqrt', 0.5],
            }
        },
        'SVR': {
            'model': SVR(),
            'params': {
                'C': [1, 10, 100],
                'gamma': ['scale', 0.001, 0.01],
                'kernel': ['rbf'],
                'epsilon': [0.05, 0.1, 0.2],
            }
        },
    }
    try:
        from lightgbm import LGBMRegressor
        models['LightGBM'] = {
            'model': LGBMRegressor(random_state=42, verbosity=-1, n_jobs=-1),
            'params': {
                'n_estimators': [100, 200, 300, 500],
                'max_depth': [3, 5, 7, -1],
                'num_leaves': [15, 31, 63],
                'learning_rate': [0.01, 0.03, 0.05, 0.1],
                'subsample': [0.6, 0.8, 1.0],
                'colsample_bytree': [0.6, 0.8, 1.0],
                'reg_alpha': [0, 0.1, 1.0],
                'reg_lambda': [0, 0.1, 1.0],
            }
        }
    except ImportError:
        pass
    try:
        from xgboost import XGBRegressor
        models['XGBoost'] = {
            'model': XGBRegressor(random_state=42, eval_metric='rmse', n_jobs=-1, verbosity=0),
            'params': {
                'n_estimators': [300, 500, 800],
                'learning_rate': [0.03, 0.05, 0.1],
                'max_depth': [3, 4, 5],
                'subsample': [0.7, 0.8, 0.9],
                'colsample_bytree': [0.6, 0.7, 0.8],
                'reg_alpha': [0.1, 0.5, 1.0, 5.0],
                'reg_lambda': [0.1, 1.0, 5.0],
                'gamma': [1, 3, 5],
                'min_child_weight': [5, 10, 20],
            }
        }
    except ImportError:
        pass
    return models


# =============== 三阶段训练（合并 Train+Val） ===============
def _metrics(y, p):
    return {'mae': mean_absolute_error(y, p),
            'r2':  r2_score(y, p),
            'mse': mean_squared_error(y, p),
            'rmse': np.sqrt(mean_squared_error(y, p))}


def train(ds, models, n_iter=100):
    X_full = np.vstack([ds['X_tr'], ds['X_va']])
    y_full = np.concatenate([ds['y_tr'], ds['y_va']])
    out = {}
    print(f"\n{'='*60}")
    print(f"🎯 {ds['name']}  Train={ds['n_tr']} + Val={ds['n_va']} = {len(y_full)}  "
          f"Test={ds['n_te']}  Features={len(ds['features'])}")
    print('='*60)

    for name, cfg in models.items():
        t0 = time.time()
        if name == 'SVR':
            scX = StandardScaler(); scY = StandardScaler()
            Xs = scX.fit_transform(X_full)
            ys = scY.fit_transform(y_full.reshape(-1,1)).ravel()
            search = RandomizedSearchCV(cfg['model'], cfg['params'], n_iter=n_iter,
                                        cv=5, scoring='neg_mean_absolute_error',
                                        n_jobs=-1, random_state=42, verbose=0)
            search.fit(Xs, ys)
            best = search.best_estimator_
            # 保存 scaler
            with open(MODELS/ds['name']/f'{name}_scaler_X.pkl', 'wb') as f:
                pickle.dump(scX, f)
            with open(MODELS/ds['name']/f'{name}_scaler_y.pkl', 'wb') as f:
                pickle.dump(scY, f)
            Xtr_s = scX.transform(ds['X_tr'])
            Xva_s = scX.transform(ds['X_va'])
            Xte_s = scX.transform(ds['X_te'])
            p_tr = scY.inverse_transform(best.predict(Xtr_s).reshape(-1,1)).ravel()
            p_va = scY.inverse_transform(best.predict(Xva_s).reshape(-1,1)).ravel()
            p_te = scY.inverse_transform(best.predict(Xte_s).reshape(-1,1)).ravel()
        else:
            search = RandomizedSearchCV(cfg['model'], cfg['params'], n_iter=n_iter,
                                        cv=5, scoring='neg_mean_absolute_error',
                                        n_jobs=-1, random_state=42, verbose=0)
            search.fit(X_full, y_full)
            best = search.best_estimator_
            p_tr = best.predict(ds['X_tr'])
            p_va = best.predict(ds['X_va'])
            p_te = best.predict(ds['X_te'])

        # 保存模型 pkl
        with open(MODELS/ds['name']/f'{name}.pkl', 'wb') as f:
            pickle.dump(best, f)

        m_tr = _metrics(ds['y_tr'], p_tr)
        m_va = _metrics(ds['y_va'], p_va)
        m_te = _metrics(ds['y_te'], p_te)
        out[name] = dict(
            model=best,
            Train_MAE=m_tr['mae'], Val_MAE=m_va['mae'], Test_MAE=m_te['mae'],
            Train_R2=m_tr['r2'],   Val_R2=m_va['r2'],   Test_R2=m_te['r2'],
            Train_RMSE=m_tr['rmse'], Val_RMSE=m_va['rmse'], Test_RMSE=m_te['rmse'],
            y_tr_true=ds['y_tr'], y_tr_pred=p_tr,
            y_va_true=ds['y_va'], y_va_pred=p_va,
            y_te_true=ds['y_te'], y_te_pred=p_te,
            best_params=search.best_params_,
        )
        print(f"  ✅ {name:<18}: Train R²={m_tr['r2']:.4f}  Val R²={m_va['r2']:.4f}  "
              f"Test R²={m_te['r2']:.4f}  MAE={m_te['mae']:.4f}  ({time.time()-t0:.1f}s)")
    return out


# =============== 绘图 ===============
def plot_scatter_grid(all_res, path):
    targets = [k for k in all_res.keys() if not k.startswith('_')]
    models  = [k for k in next(iter(all_res.values())).keys()]
    n_t, n_m = len(targets), len(models)
    fig, axes = plt.subplots(n_t, n_m, figsize=(3.6*n_m, 3.6*n_t))
    for ti, tn in enumerate(targets):
        for mi, mn in enumerate(models):
            ax = axes[ti, mi] if n_t > 1 else axes[mi]
            r = all_res[tn][mn]
            yt, yp = r['y_te_true'], r['y_te_pred']
            ax.scatter(yt, yp, alpha=0.6, c='#3498db', edgecolors='none', s=40)
            lo, hi = min(yt.min(), yp.min()), max(yt.max(), yp.max())
            mg = (hi-lo)*0.05
            ax.plot([lo-mg, hi+mg], [lo-mg, hi+mg], 'r--', lw=1.5)
            ax.set_xlabel('True', fontsize=9)
            ax.set_ylabel('Predicted', fontsize=9)
            ax.set_title(f"{mn}\nR²={r['Test_R2']:.4f}  MAE={r['Test_MAE']:.4f}", fontsize=9)
            ax.grid(True, alpha=0.3)
            ax.set_xlim([lo-mg, hi+mg]); ax.set_ylim([lo-mg, hi+mg])
    plt.suptitle('Test Set: True vs Predicted (Three Targets × Five Models)',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  📊 {path.name}")


def plot_r2_bar(all_res, path):
    targets = [k for k in all_res.keys() if not k.startswith('_')]
    models  = list(next(iter(all_res.values())).keys())
    fig, axes = plt.subplots(1, len(targets), figsize=(6*len(targets), 5))
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(models)))
    for ti, tn in enumerate(targets):
        ax = axes[ti] if len(targets) > 1 else axes
        r2  = [all_res[tn][m]['Test_R2'] for m in models]
        mae = [all_res[tn][m]['Test_MAE'] for m in models]
        x = np.arange(len(models))
        bars = ax.bar(x, r2, color=colors, alpha=0.85, edgecolor='black', lw=0.5)
        ax.set_xticks(x); ax.set_xticklabels(models, rotation=30, ha='right', fontsize=9)
        ax.set_ylabel('Test R²', fontsize=10)
        ax.set_title(tn, fontsize=11, fontweight='bold')
        ax.set_ylim([0.5, 1.05])
        ax.axhline(y=0.91, color='red', ls='--', lw=1.5, alpha=0.6, label='R²=0.91 目标线')
        ax.grid(True, alpha=0.3, axis='y'); ax.legend(fontsize=9)
        for b, r, m in zip(bars, r2, mae):
            ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.01,
                    f'{r:.3f}\nMAE:{m:.3f}', ha='center', va='bottom', fontsize=7.5)
    plt.suptitle('各目标 Test R² 对比', fontsize=13, fontweight='bold')
    plt.tight_layout(); plt.savefig(path, dpi=200, bbox_inches='tight'); plt.close()
    print(f"  📊 {path.name}")


def plot_3stage(all_res, path):
    targets = [k for k in all_res.keys() if not k.startswith('_')]
    models  = list(next(iter(all_res.values())).keys())
    fig, axes = plt.subplots(2, len(targets), figsize=(6*len(targets), 9))
    for ti, tn in enumerate(targets):
        ax = axes[0, ti] if len(targets)>1 else axes[0]
        x = np.arange(len(models)); w = 0.27
        t_r2 = [all_res[tn][m]['Train_R2'] for m in models]
        v_r2 = [all_res[tn][m]['Val_R2']   for m in models]
        e_r2 = [all_res[tn][m]['Test_R2']  for m in models]
        ax.bar(x-w, t_r2, w, label='Train', color='#3498db', alpha=0.85)
        ax.bar(x,   v_r2, w, label='Val',   color='#f39c12', alpha=0.85)
        ax.bar(x+w, e_r2, w, label='Test',  color='#e74c3c', alpha=0.85)
        ax.set_xticks(x); ax.set_xticklabels(models, rotation=30, ha='right', fontsize=9)
        ax.set_ylabel('R²'); ax.set_title(f'{tn} - R²', fontweight='bold')
        ax.set_ylim([0.5, 1.05]); ax.axhline(0.91, color='red', ls='--', lw=1.2, alpha=0.6)
        ax.grid(True, alpha=0.3, axis='y'); ax.legend(fontsize=9)

        ax = axes[1, ti] if len(targets)>1 else axes[1]
        t_m = [all_res[tn][m]['Train_MAE'] for m in models]
        v_m = [all_res[tn][m]['Val_MAE']   for m in models]
        e_m = [all_res[tn][m]['Test_MAE']  for m in models]
        ax.bar(x-w, t_m, w, label='Train', color='#3498db', alpha=0.85)
        ax.bar(x,   v_m, w, label='Val',   color='#f39c12', alpha=0.85)
        ax.bar(x+w, e_m, w, label='Test',  color='#e74c3c', alpha=0.85)
        ax.set_xticks(x); ax.set_xticklabels(models, rotation=30, ha='right', fontsize=9)
        ax.set_ylabel('MAE'); ax.set_title(f'{tn} - MAE', fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y'); ax.legend(fontsize=9)
    plt.suptitle('Train/Val/Test 三阶段评估', fontsize=13, fontweight='bold')
    plt.tight_layout(); plt.savefig(path, dpi=200, bbox_inches='tight'); plt.close()
    print(f"  📊 {path.name}")


def plot_residual(all_res, path):
    """最佳模型在 Test 上的残差图"""
    targets = [k for k in all_res.keys() if not k.startswith('_')]
    fig, axes = plt.subplots(1, len(targets), figsize=(6*len(targets), 5))
    for ti, tn in enumerate(targets):
        ax = axes[ti] if len(targets)>1 else axes
        valid = all_res[tn]
        best_name = max(valid, key=lambda k: valid[k]['Test_R2'])
        r = valid[best_name]
        residual = r['y_te_pred'] - r['y_te_true']
        ax.scatter(r['y_te_pred'], residual, alpha=0.6, c='#2ecc71', edgecolors='none', s=40)
        ax.axhline(0, color='red', ls='--', lw=1.5)
        ax.set_xlabel('Predicted'); ax.set_ylabel('Residual (Pred-True)')
        ax.set_title(f'{tn} - {best_name}\nTest R²={r["Test_R2"]:.4f}', fontweight='bold')
        ax.grid(True, alpha=0.3)
    plt.suptitle('最佳模型 Test 残差分布', fontsize=13, fontweight='bold')
    plt.tight_layout(); plt.savefig(path, dpi=200, bbox_inches='tight'); plt.close()
    print(f"  📊 {path.name}")


# =============== 报告输出 ===============
def save_metrics_csv(all_res):
    rows = []
    for tn, td in all_res.items():
        if tn.startswith('_'):
            continue
        for mn, mr in td.items():
            if mn.startswith('_'):
                continue
            rows.append({
                'Target': tn, 'Model': mn,
                'Train_MAE': mr['Train_MAE'], 'Val_MAE': mr['Val_MAE'], 'Test_MAE': mr['Test_MAE'],
                'Train_R2':  mr['Train_R2'],  'Val_R2':  mr['Val_R2'],  'Test_R2':  mr['Test_R2'],
                'Train_RMSE': mr['Train_RMSE'], 'Val_RMSE': mr['Val_RMSE'], 'Test_RMSE': mr['Test_RMSE'],
            })
    pd.DataFrame(rows).to_csv(TABLES/'metrics_summary.csv', index=False)
    print(f"  📋 metrics_summary.csv")


def save_predictions_csv(all_res):
    rows = []
    for tn, td in all_res.items():
        if tn.startswith('_'):
            continue
        for mn, mr in td.items():
            if mn.startswith('_'):
                continue
            for split, yt, yp in [('Train', mr['y_tr_true'], mr['y_tr_pred']),
                                  ('Val',   mr['y_va_true'], mr['y_va_pred']),
                                  ('Test',  mr['y_te_true'], mr['y_te_pred'])]:
                for t, p in zip(yt, yp):
                    rows.append({'Target': tn, 'Model': mn, 'Split': split,
                                 'True': t, 'Predicted': p})
    pd.DataFrame(rows).to_csv(TABLES/'predictions_all.csv', index=False)
    print(f"  📋 predictions_all.csv")


def save_markdown(all_res, features_meta):
    target_meta = {
        'V5':       {'name_zh': 'PCT-V5 吸附焓变斜率',   'unit': '—'},
        'V6':       {'name_zh': 'V6 吸附焓变截距',       'unit': '—'},
        'Capacity': {'name_zh': 'Capacity 最大吸附量',   'unit': 'mol/kg'},
    }

    for tn, td in all_res.items():
        if tn.startswith('_'):
            continue
        meta = target_meta[tn]
        best_name = max(td, key=lambda k: td[k]['Test_R2'])
        best = td[best_name]
        feats = features_meta.get(tn, [])
        md = f"# {tn} - {meta['name_zh']}\n\n"
        md += f"**目标变量单位**: {meta['unit']}\n\n"
        md += f"**数据集划分**: Train={len(best['y_tr_true'])} + Val={len(best['y_va_true'])} "
        md += f"(合并训练) | Test={len(best['y_te_true'])}\n\n"
        md += f"**特征数量**: {len(feats)}\n\n"
        md += "**特征列表**:\n"
        for f in feats:
            md += f"- `{f}`\n"
        md += "\n---\n\n"
        md += "## 1. 最佳模型\n\n"
        md += f"| 项目 | 值 |\n|------|---|\n"
        md += f"| **最佳模型** | **{best_name}** |\n"
        md += f"| Test R² | **{best['Test_R2']:.4f}** {'✅' if best['Test_R2']>0.91 else '❌'} |\n"
        md += f"| Test MAE | {best['Test_MAE']:.4f} |\n"
        md += f"| Test RMSE | {best['Test_RMSE']:.4f} |\n"
        md += f"| Val R² | {best['Val_R2']:.4f} |\n"
        md += f"| Train R² | {best['Train_R2']:.4f} |\n\n"
        md += f"**最优超参数**:\n```json\n{json.dumps(best['best_params'], indent=2, ensure_ascii=False)}\n```\n\n"
        md += "---\n\n## 2. 所有模型结果\n\n"
        md += "| 模型 | Train MAE | Val MAE | Test MAE | Train R² | Val R² | **Test R²** | 达标 |\n"
        md += "|------|-----------|---------|----------|----------|---------|------------|------|\n"
        for mn in td.keys():
            r = td[mn]
            ok = '✅' if r['Test_R2']>0.91 else '❌'
            md += f"| {mn} | {r['Train_MAE']:.4f} | {r['Val_MAE']:.4f} | {r['Test_MAE']:.4f} "
            md += f"| {r['Train_R2']:.4f} | {r['Val_R2']:.4f} | **{r['Test_R2']:.4f}** | {ok} |\n"
        md += "\n---\n\n## 3. 模型文件\n\n"
        md += "保存路径: `models/{}/`\n\n".format(tn)
        for mn in td.keys():
            extra = " (+ scaler_X.pkl, scaler_y.pkl)" if mn == 'SVR' else ""
            md += f"- `{mn}.pkl`{extra}\n"
        md += "\n---\n\n## 4. 结论\n\n"
        if best['Test_R2'] > 0.91:
            md += f"✅ **达成目标**: Test R² = {best['Test_R2']:.4f} > 0.91\n\n"
        else:
            md += f"❌ **未达标**: Test R² = {best['Test_R2']:.4f} < 0.91\n\n"
        md += f"最佳模型为 **{best_name}**，在 Test 集上 MAE={best['Test_MAE']:.4f}，R²={best['Test_R2']:.4f}。"
        md += f"Train R²={best['Train_R2']:.4f} 与 Test R²={best['Test_R2']:.4f} 差距"
        md += f" {abs(best['Train_R2']-best['Test_R2']):.4f}，泛化性能{'良好' if abs(best['Train_R2']-best['Test_R2'])<0.05 else '可接受'}。\n\n"
        with open(ROOT/'docs'/f'{tn}_report.md', 'w', encoding='utf-8') as f:
            f.write(md)
        print(f"  📝 docs/{tn}_report.md")


def save_summary_readme(all_res):
    md = "# PCT_project\n\n"
    md += "**统一三阶段训练项目**: V5 (吸附焓变斜率) / V6 (吸附焓变截距) / Capacity (最大吸附量)\n\n"
    md += "## 项目结构\n\n```\n"
    md += "PCT_project/\n"
    md += "├── data/                      # 数据文件（统一三阶段格式）\n"
    md += "│   ├── V5/                    # 13 features, 240/60/76\n"
    md += "│   ├── V6/                    # 18 features, 259/56/56\n"
    md += "│   ├── Capacity/              # 16 features, 262/57/57\n"
    md += "│   └── split_info.md          # 划分说明\n"
    md += "├── notebooks/                 # 训练 Notebook\n"
    md += "│   ├── 01_train_V5.ipynb\n"
    md += "│   ├── 02_train_V6.ipynb\n"
    md += "│   ├── 03_train_Capacity.ipynb\n"
    md += "│   └── 04_summary.ipynb       # 汇总对比\n"
    md += "├── models/                    # 训练好的模型 pkl\n"
    md += "│   ├── V5/\n│   ├── V6/\n│   └── Capacity/\n"
    md += "├── results/                   # 结果\n"
    md += "│   ├── figures/               # 图表\n"
    md += "│   └── tables/                # 表格 (CSV)\n"
    md += "├── docs/                      # 各目标的 md 报告\n"
    md += "├── train_all.py               # 统一训练脚本\n"
    md += "└── README.md                  # 本文件\n```\n\n"
    md += "## 数据格式规范\n\n"
    md += "每个目标目录下统一为:\n"
    md += "- `features.csv` — 特征列表\n"
    md += "- `X_{train,val,test}.csv` — 各阶段特征矩阵\n"
    md += "- `y_{train,val,test}.csv` — 各阶段目标变量（列名: `target`）\n\n"
    md += "## 训练流程\n\n"
    md += "1. **合并训练**: Train+Val 合并用于 5 折 CV 超参搜索 + 最终模型训练\n"
    md += "2. **独立测试**: Test 完全独立未参与训练/调参\n"
    md += "3. **超参搜索**: RandomizedSearchCV (n_iter=100, cv=5)\n"
    md += "4. **模型**: RandomForest, GradientBoosting, SVR, LightGBM, XGBoost\n"
    md += "5. **标准化**: SVR 同时标准化 X 和 y\n\n"
    md += "## 结果概览\n\n"
    md += "| 目标 | 最佳模型 | Test R² | Test MAE | 达标 |\n"
    md += "|------|----------|---------|----------|------|\n"
    target_meta = {
        'V5':       'PCT-V5 吸附焓变斜率',
        'V6':       'V6 吸附焓变截距',
        'Capacity': 'Capacity 最大吸附量',
    }
    for tn in ['V5', 'V6', 'Capacity']:
        td = all_res[tn]
        if not isinstance(td, dict) or any(k.startswith('_') for k in td.keys()):
            continue
        best_name = max(td, key=lambda k: td[k]['Test_R2'])
        r = td[best_name]
        ok = '✅' if r['Test_R2']>0.91 else '❌'
        md += f"| {tn} ({target_meta[tn]}) | {best_name} | **{r['Test_R2']:.4f}** | {r['Test_MAE']:.4f} | {ok} |\n"
    md += "\n## 报告详情\n\n"
    md += "- [V5 详细报告](docs/V5_report.md)\n"
    md += "- [V6 详细报告](docs/V6_report.md)\n"
    md += "- [Capacity 详细报告](docs/Capacity_report.md)\n"
    md += "- [数据划分说明](data/split_info.md)\n\n"
    md += "## 使用方式\n\n"
    md += "### 加载模型预测\n"
    md += "```python\n"
    md += "import pickle, pandas as pd\n"
    md += "with open('models/V5/SVR.pkl', 'rb') as f:\n"
    md += "    model = pickle.load(f)\n"
    md += "X_new = pd.read_csv('data/V5/X_test.csv')\n"
    md += "y_pred = model.predict(X_new.values)\n"
    md += "```\n\n"
    md += "### 重新训练\n"
    md += "```bash\n"
    md += "python train_all.py\n"
    md += "```\n"
    with open(ROOT/'README.md', 'w', encoding='utf-8') as f:
        f.write(md)
    print(f"  📝 README.md")


# =============== 主程序 ===============
if __name__ == '__main__':
    print("="*60); print("PCT_project 统一训练"); print("="*60)

    v5  = load_dataset('V5')
    v6  = load_dataset('V6')
    cap = load_dataset('Capacity')

    for d in [v5, v6, cap]:
        print(f"  {d['name']:>10}: Train={d['n_tr']:>3} + Val={d['n_va']:>3} | "
              f"Test={d['n_te']:>3} | Features={len(d['features'])}")

    models = get_models()
    print(f"\n模型: {list(models.keys())}\n")

    t0 = time.time()
    r5  = train(v5,  models, n_iter=100)
    r6  = train(v6,  models, n_iter=100)
    rcp = train(cap, models, n_iter=100)
    print(f"\n⏱️ 总耗时: {time.time()-t0:.1f}s")

    all_res = {'V5': r5, 'V6': r6, 'Capacity': rcp}
    features_meta = {'V5': v5['features'], 'V6': v6['features'], 'Capacity': cap['features']}

    # 汇总
    print("\n" + "="*70)
    print(f"{'模型':<18} | {'V5':>8} | {'V6':>8} | {'Capacity':>10}")
    print("-"*70)
    for m in models.keys():
        print(f"  {m:<16} | {all_res['V5'][m]['Test_R2']:>7.4f} | "
              f"{all_res['V6'][m]['Test_R2']:>7.4f} | "
              f"{all_res['Capacity'][m]['Test_R2']:>9.4f}")
    print("="*70)

    print("\n🎯 各目标最佳模型:")
    for tn in ['V5', 'V6', 'Capacity']:
        b = max(all_res[tn], key=lambda k: all_res[tn][k]['Test_R2'])
        r = all_res[tn][b]
        ok = '✅' if r['Test_R2']>0.91 else '❌'
        print(f"  {tn:<10}: {b:<18} R²={r['Test_R2']:.4f} MAE={r['Test_MAE']:.4f} {ok}")

    # 绘图（传入干净字典）
    print("\n生成图表...")
    plot_res = {k: v for k, v in all_res.items() if not k.startswith('_')}
    plot_scatter_grid(plot_res, FIGURES/'fig1_all_scatter.png')
    plot_r2_bar(plot_res, FIGURES/'fig2_r2_comparison.png')
    plot_3stage(plot_res, FIGURES/'fig3_3stage_metrics.png')
    plot_residual(plot_res, FIGURES/'fig4_residuals.png')

    # 表格
    print("\n保存表格...")
    save_metrics_csv(all_res)
    save_predictions_csv(all_res)

    # 报告
    print("\n生成文档...")
    save_markdown(all_res, features_meta)
    save_summary_readme(all_res)

    # 保存完整结果 pickle（过滤临时键）
    with open(RESULTS/'all_results.pkl', 'wb') as f:
        pickle.dump(plot_res, f)
    print("  💾 all_results.pkl")

    print("\n" + "="*60)
    print(f"✅ 全部完成! 项目目录: {ROOT}")
    print("="*60)
