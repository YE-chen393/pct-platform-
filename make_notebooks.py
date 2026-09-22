# -*- coding: utf-8 -*-
"""根据 train_all.py 生成对应的 Jupyter Notebook 文件

用法:
    PYTHONPATH=. python make_notebooks.py

生成的 notebook 会写到 ./notebooks/ 目录下(相对当前工作目录的 PCT_project/)。
"""
import json
from pathlib import Path

# 让脚本独立运行时也能 import pct_app
import sys
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# 用 pct_app/config/paths 提供的 ROOT(自动以本文件位置为基准)
from pct_app.config.paths import ROOT as _PCT_ROOT

ROOT = _PCT_ROOT
NB_DIR = ROOT / 'notebooks'
NB_DIR.mkdir(exist_ok=True)


def make_notebook(cells):
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return nb


def md_cell(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src}


def code_cell(src, outputs=None):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": outputs or [],
        "source": src,
    }


# =============== 通用前置 cells ===============
# 把 ROOT 替换成占位符 {NB_ROOT},生成 notebook 时再填实际路径
NB_ROOT_PLACEHOLDER = "{NB_ROOT}"

common_setup = [
    md_cell("# PCT_project - 统一训练 Notebook\n\n"
            "本 Notebook 对应 `train_all.py` 的训练逻辑，按目标分别训练 V5、V6、Capacity。\n\n"
            f"**项目目录**: `{NB_ROOT_PLACEHOLDER}`\n\n"
            "**数据格式**: 三阶段统一 (Train / Val / Test)\n"),
    code_cell(f"""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pickle, json, time, warnings
warnings.filterwarnings('ignore')

from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
from sklearn.model_selection import RandomizedSearchCV

plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

ROOT    = Path(r'{NB_ROOT_PLACEHOLDER}')
DATA    = ROOT / 'data'
MODELS  = ROOT / 'models'
RESULTS = ROOT / 'results'
FIGURES = RESULTS / 'figures'
TABLES  = RESULTS / 'tables'

for d in [MODELS/'V5', MODELS/'V6', MODELS/'Capacity', FIGURES, TABLES]:
    d.mkdir(parents=True, exist_ok=True)

print("✅ 环境准备完成")"""),
    md_cell("## 数据加载\n\n"
            "统一从 `data/<Target>/` 读取 Train/Val/Test CSV。"),
    code_cell("""def load_dataset(name):
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
                n_tr=len(y_tr), n_va=len(y_va), n_te=len(y_te))"""),
]


# =============== 模型与训练函数 ===============
model_setup = [
    md_cell("## 模型与训练函数\n"),
    code_cell("""def get_models():
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


def _metrics(y, p):
    return {'mae': mean_absolute_error(y, p),
            'r2':  r2_score(y, p),
            'mse': mean_squared_error(y, p),
            'rmse': np.sqrt(mean_squared_error(y, p))}


def train(ds, models, n_iter=100):
    X_full = np.vstack([ds['X_tr'], ds['X_va']])
    y_full = np.concatenate([ds['y_tr'], ds['y_va']])
    out = {}
    print(f"\\n{'='*60}")
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
        with open(MODELS/ds['name']/f'{name}.pkl', 'wb') as f:
            pickle.dump(best, f)
        m_tr = _metrics(ds['y_tr'], p_tr)
        m_va = _metrics(ds['y_va'], p_va)
        m_te = _metrics(ds['y_te'], p_te)
        out[name] = dict(model=best,
            Train_MAE=m_tr['mae'], Val_MAE=m_va['mae'], Test_MAE=m_te['mae'],
            Train_R2=m_tr['r2'], Val_R2=m_va['r2'], Test_R2=m_te['r2'],
            Train_RMSE=m_tr['rmse'], Val_RMSE=m_va['rmse'], Test_RMSE=m_te['rmse'],
            y_tr_true=ds['y_tr'], y_tr_pred=p_tr,
            y_va_true=ds['y_va'], y_va_pred=p_va,
            y_te_true=ds['y_te'], y_te_pred=p_te,
            best_params=search.best_params_)
        print(f"  ✅ {name:<18}: Train R²={m_tr['r2']:.4f}  Val R²={m_va['r2']:.4f}  "
              f"Test R²={m_te['r2']:.4f}  MAE={m_te['mae']:.4f}  ({time.time()-t0:.1f}s)")
    return out"""),
]


# =============== 绘图与汇总函数 ===============
viz_setup = [
    md_cell("## 可视化与汇总\n"),
    code_cell("""def plot_target(res, name, outdir):
    \"\"\"为单个目标绘制 4 张图\"\"\"
    models = list(res.keys())

    # 散点图
    fig, axes = plt.subplots(1, len(models), figsize=(3.6*len(models), 3.6))
    for mi, mn in enumerate(models):
        ax = axes[mi]
        r = res[mn]
        yt, yp = r['y_te_true'], r['y_te_pred']
        ax.scatter(yt, yp, alpha=0.6, c='#3498db', edgecolors='none', s=40)
        lo, hi = min(yt.min(), yp.min()), max(yt.max(), yp.max())
        mg = (hi-lo)*0.05
        ax.plot([lo-mg, hi+mg], [lo-mg, hi+mg], 'r--', lw=1.5)
        ax.set_xlabel('True'); ax.set_ylabel('Predicted')
        ax.set_title(f\"{mn}\\nR²={r['Test_R2']:.4f}  MAE={r['Test_MAE']:.4f}\")
        ax.grid(True, alpha=0.3)
        ax.set_xlim([lo-mg, hi+mg]); ax.set_ylim([lo-mg, hi+mg])
    plt.suptitle(f'{name} - Test Predicted vs True', fontweight='bold')
    plt.tight_layout(); plt.savefig(outdir/f'fig_{name}_scatter.png', dpi=200, bbox_inches='tight'); plt.close()

    # R² 条形图
    fig, ax = plt.subplots(figsize=(7, 5))
    r2  = [res[m]['Test_R2'] for m in models]
    mae = [res[m]['Test_MAE'] for m in models]
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(models)))
    x = np.arange(len(models))
    bars = ax.bar(x, r2, color=colors, alpha=0.85, edgecolor='black', lw=0.5)
    ax.set_xticks(x); ax.set_xticklabels(models, rotation=30, ha='right')
    ax.set_ylabel('Test R²'); ax.set_title(f'{name} - Test R² (Target=0.91)')
    ax.set_ylim([0.5, 1.05])
    ax.axhline(0.91, color='red', ls='--', lw=1.5, alpha=0.6, label='R²=0.91')
    ax.grid(True, alpha=0.3, axis='y'); ax.legend()
    for b, r, m in zip(bars, r2, mae):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.01, f'{r:.3f}\\nMAE:{m:.3f}',
                ha='center', va='bottom', fontsize=8)
    plt.tight_layout(); plt.savefig(outdir/f'fig_{name}_r2.png', dpi=200, bbox_inches='tight'); plt.close()

    # 三阶段 R²/MAE
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    w = 0.27
    for ax_i, (metric, color_label) in enumerate([('R²', 'R²'), ('MAE', 'MAE')]):
        ax = axes[ax_i]
        if metric == 'R²':
            t = [res[m]['Train_R2'] for m in models]
            v = [res[m]['Val_R2']   for m in models]
            e = [res[m]['Test_R2']  for m in models]
            ax.set_ylim([0.5, 1.05]); ax.axhline(0.91, color='red', ls='--', lw=1.2, alpha=0.6)
        else:
            t = [res[m]['Train_MAE'] for m in models]
            v = [res[m]['Val_MAE']   for m in models]
            e = [res[m]['Test_MAE']  for m in models]
        ax.bar(x-w, t, w, label='Train', color='#3498db', alpha=0.85)
        ax.bar(x,   v, w, label='Val',   color='#f39c12', alpha=0.85)
        ax.bar(x+w, e, w, label='Test',  color='#e74c3c', alpha=0.85)
        ax.set_xticks(x); ax.set_xticklabels(models, rotation=30, ha='right')
        ax.set_ylabel(metric); ax.set_title(f'{name} - {metric}')
        ax.grid(True, alpha=0.3, axis='y'); ax.legend()
    plt.suptitle(f'{name} - Train/Val/Test', fontweight='bold')
    plt.tight_layout(); plt.savefig(outdir/f'fig_{name}_3stage.png', dpi=200, bbox_inches='tight'); plt.close()
    print(f'  📊 {name} 3 张图已生成')"""),
]


def make_target_nb(name, label):
    cells = common_setup + model_setup + viz_setup + [
        md_cell(f"## {label} 目标训练\n\n"
                f"加载 `{name}` 数据集，训练所有模型，保存 pkl 并生成图表。"),
        code_cell("""ds = load_dataset('""" + name + """')
print(f"数据: Train={ds['n_tr']}  Val={ds['n_va']}  Test={ds['n_te']}  Features={len(ds['features'])}")
print('特征列表:')
for f in ds['features']: print(' -', f)"""),
        code_cell("""models = get_models()
results = train(ds, models, n_iter=100)"""),
        md_cell(f"### 最佳模型\n"),
        code_cell("""best = max(results, key=lambda k: results[k]['Test_R2'])
print(f"最佳模型: {best}")
print(f"Test R²   : {results[best]['Test_R2']:.4f}")
print(f"Test MAE  : {results[best]['Test_MAE']:.4f}")
print(f"Test RMSE : {results[best]['Test_RMSE']:.4f}")
print('最优超参数:', results[best]['best_params'])"""),
        md_cell("### 全部模型结果表"),
        code_cell("""summary = pd.DataFrame([{
    'Model': m,
    'Train_MAE': r['Train_MAE'], 'Val_MAE': r['Val_MAE'], 'Test_MAE': r['Test_MAE'],
    'Train_R2': r['Train_R2'], 'Val_R2': r['Val_R2'], 'Test_R2': r['Test_R2'],
} for m, r in results.items()])
display(summary.round(4))
summary.to_csv(TABLES/f'metrics_{name}.csv', index=False)"""),
        md_cell("### 图表生成"),
        code_cell("plot_target(results, '" + name + "', FIGURES)"),
        md_cell("### 加载模型预测示例"),
        code_cell("""import pickle
with open(MODELS/'""" + name + """'/'__BEST__.pkl', 'rb') as f:
    model = pickle.load(f)

X_new = pd.read_csv(DATA/'""" + name + """'/'X_test.csv').values
y_pred_new = model.predict(X_new)
print('预测前 5 个样本:', y_pred_new[:5])
# 注: __BEST__ 需替换为实际最佳模型名 (best = max(results, ...))"""),
    ]
    return make_notebook(cells)


# 生成三个目标 notebook + 汇总
nb_v5  = make_target_nb('V5',       'V5 - 吸附焓变斜率')
nb_v6  = make_target_nb('V6',       'V6 - 吸附焓变截距')
nb_cap = make_target_nb('Capacity', 'Capacity - 最大吸附量')

with open(NB_DIR/'01_train_V5.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb_v5, f, ensure_ascii=False)
with open(NB_DIR/'02_train_V6.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb_v6, f, ensure_ascii=False)
with open(NB_DIR/'03_train_Capacity.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb_cap, f, ensure_ascii=False)

# 汇总 notebook
summary_cells = common_setup[:2] + [
    md_cell("# 汇总 Notebook\n\n"
            "对比 V5/V6/Capacity 三个目标的训练结果。"),
    code_cell(f"""import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(r'{NB_ROOT_PLACEHOLDER}')
TABLES = ROOT / 'results' / 'tables'
FIGURES = ROOT / 'results' / 'figures'

df = pd.read_csv(TABLES / 'metrics_summary.csv')
display(df.round(4))"""),
    md_cell("### 各目标最佳模型"),
    code_cell("""best_per_target = df.loc[df.groupby('Target')['Test_R2'].idxmax()]
display(best_per_target[['Target','Model','Test_R2','Test_MAE','Test_RMSE']])"""),
    md_cell("### 最佳模型散点图（汇总）"),
    code_cell("""from PIL import Image
import matplotlib.pyplot as plt
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for i, t in enumerate(['V5','V6','Capacity']):
    axes[i].imshow(Image.open(FIGURES/f'fig_{t}_scatter.png'))
    axes[i].axis('off')
    axes[i].set_title(t, fontweight='bold')
plt.tight_layout()
plt.show()"""),
]
with open(NB_DIR/'04_summary.ipynb', 'w', encoding='utf-8') as f:
    json.dump(make_notebook(summary_cells), f, ensure_ascii=False)

# ========= 把 ROOT 占位符替换成实际路径(写到磁盘前再 patch 一次) =========
def _sub_root(nb_obj, real_root: str):
    """递归把所有 source 字符串里的 {NB_ROOT} 替换成实际路径。"""
    nb_str = json.dumps(nb_obj, ensure_ascii=False)
    nb_str = nb_str.replace(NB_ROOT_PLACEHOLDER, real_root)
    return json.loads(nb_str)

for nb_name in ('01_train_V5.ipynb', '02_train_V6.ipynb',
                '03_train_Capacity.ipynb', '04_summary.ipynb'):
    nb_path = NB_DIR / nb_name
    if not nb_path.exists():
        continue
    nb_obj = json.loads(nb_path.read_text(encoding='utf-8'))
    nb_obj = _sub_root(nb_obj, str(ROOT).replace("\\", "/"))
    nb_path.write_text(json.dumps(nb_obj, ensure_ascii=False), encoding='utf-8')

print("✅ 4 个 Notebook 已生成:")
for f in sorted(NB_DIR.glob('*.ipynb')):
    print(f"   - {f}")
