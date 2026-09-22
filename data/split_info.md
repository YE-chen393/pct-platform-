# 统一数据划分信息

## 格式规范
每个数据集目录下:
- features.csv: 特征列表
- X_{train,val,test}.csv: 各阶段特征
- y_{train,val,test}.csv: 各阶段目标 (列名: target)

## 划分策略
| 数据集 | 目标变量 | 特征数 | 划分方式 |
|--------|----------|--------|----------|
| V5 | 吸附焓变斜率 | 13 | Train:Val:Test = 240:60:76 (原始 Train 80/20 划分 Val) |
| V6 | 吸附焓变截距 | 18 | Train:Val:Test = 259:56:56 (沿用原始划分) |
| Capacity | 最大吸附量 | 16 | Train:Val:Test = 262:57:57 (沿用原始划分) |

## 随机种子
- V5 的 Train/Val 划分: random_state=42, test_size=0.2
- V6/Capacity 沿用原始 split 文件

## 特征列表（按数据集）
### V5 (13 个特征)
- MagpieData avg_dev NdUnfilled
- MagpieData mean NUnfilled
- MagpieData mode AtomicWeight
- MagpieData mean MendeleevNumber
- MagpieData mean MeltingT
- MagpieData mean GSvolume_pa
- MagpieData mean Electronegativity
- MagpieData mode NUnfilled
- MagpieData mean Row
- MagpieData mode MeltingT
- MagpieData mode MendeleevNumber
- V0
- MagpieData mode NdValence

### V6 (18 个特征)
- MagpieData avg_dev Column
- MagpieData minimum MeltingT
- MagpieData avg_dev NdValence
- MagpieData avg_dev NsValence
- MagpieData maximum MendeleevNumber
- MagpieData mean MendeleevNumber
- MagpieData mean NUnfilled
- MagpieData mean SpaceGroupNumber
- MagpieData minimum NUnfilled
- MagpieData avg_dev GSmagmom
- MagpieData avg_dev NdUnfilled
- MagpieData avg_dev SpaceGroupNumber
- MagpieData maximum MeltingT
- MagpieData mean MeltingT
- MagpieData mean Number
- MagpieData minimum NValence
- MagpieData mode NValence
- V0

### Capacity (16 个特征)
- MagpieData avg_dev Column
- MagpieData avg_dev CovalentRadius
- MagpieData avg_dev GSvolume_pa
- MagpieData avg_dev MeltingT
- MagpieData avg_dev NValence
- MagpieData avg_dev NdUnfilled
- MagpieData avg_dev SpaceGroupNumber
- MagpieData maximum NValence
- MagpieData mean Column
- MagpieData mean GSvolume_pa
- MagpieData mean MeltingT
- MagpieData mean MendeleevNumber
- MagpieData mode Column
- MagpieData mode MendeleevNumber
- MagpieData range Electronegativity
- V0
