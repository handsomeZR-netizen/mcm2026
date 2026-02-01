# Task 3: 职业舞者与明星特征的影响（写作骨架）

> 本文档用于Task 3写作与结果汇总。数据来自Task 1的观众投票估计与原始评委评分。

## 1. 任务目标（Problem Restatement）
- 建模量化“职业舞者（pro）”与“明星特征（年龄、行业、地区等）”对比赛结果的影响。
- 对比这些因素对**评委评分**与**观众投票**的作用是否一致。
- 用生存分析回答“celebrity 能走多远（how well a celebrity will do）”。

## 2. 数据与输入（Data Inputs）
- `data/processed/dwts_weekly_long.csv`：周度评委分与选手信息。
- `data/processed/abc_weekly_posterior.csv`：Task1反演的观众投票后验均值/方差。
- Step1输出：`data/processed/task3_weekly_model.csv`、`data/processed/task3_survival_base.csv`。

## 3. 预处理与特征工程（Key Features）
- 仅保留 `active_in_week = True` 的当周参赛者。
- **评委分标准化**：每个“赛季-周”内做 z-score（`judge_z`），消除不同周总分尺度差异。
- **行业合并**（减少稀疏）：Actor / Singer / Athlete / Reality-TV / Other。
- **地区**：US vs Non-US。
- **动态特征**：
  - `performance_trend`：本周 `judge_z` 相对上周变化。
  - `cumulative_score`：赛季内累积平均表现。
- **观众投票**：`fan_share_mean`（Task1后验均值）。

## 4. 模型方法（Method）
### 4.1 Judges Model（技术评分）
线性混合效应：
```
judge_z ~ age_z + industry + is_us + week_z + trend_z + cum_z
```
- 随机效应：pro（随机截距），同时控制 season / celebrity 的方差成分。

### 4.2 Fans Model（观众投票）
将投票占比做 logit 变换后拟合混合模型：
```
fan_logit ~ age_z + industry + is_us + week_z + trend_z + cum_z + judge_z
```
- 关键项：`judge_z` 用来检验“粉丝是否也受技术评分影响”。

### 4.3 一致性（Consistency）指标
比较 Judges vs Fans 的固定效应向量：
- **Sign Agreement**：符号一致比例。
- **Cosine Similarity**：方向相似度。
- **Pearson Corr**：线性相关性。
- **Mean Abs Gap**：平均绝对差异。

### 4.4 Pro Buff 指标
由于随机效应方差收缩（singular），最终以**固定效应残差均值**衡量 pro buff：
- `pro_buff = mean(residual | pro)`
- 附 95% CI（残差标准差 / sqrt(n)）。

### 4.5 Survival Model（Cox PH）
用“淘汰风险”回答“走多远”：
```
duration ~ age_z + mean_judge_z + mean_fan_share_z + pro_effect_z + industry + is_us
```
输出 Hazard Ratio（HR < 1 表示更不易淘汰）。

## 5. 结果汇总（Results）
### 5.1 Judges vs Fans 核心系数（标准化）
| Feature | Judges Coef | Fans Coef | 说明 |
| :-- | --: | --: | :-- |
| Age (z) | -0.003 | -0.168 | 粉丝更偏好年轻明星 |
| Week (z) | -0.111 | 0.294 | 粉丝在后期更集中投票 |
| Trend (z) | 0.395 | -0.024 | 评委更看重“进步趋势” |
| Cumulative (z) | 0.816 | 0.033 | 评委更看重“长期技术积累” |
| Judge_z (fans only) | — | 0.204 | 粉丝对评委分有正向响应 |
| Industry: Athlete | 0.013 | 0.629 | 粉丝更偏好运动员 |
| Industry: Singer | -0.001 | 0.399 | 粉丝更偏好歌手 |

**解读：**评委模型中 `trend/cum` 主导；粉丝模型中 `week/age/industry` 更突出，且 `judge_z` 对投票显著正向。

### 5.2 一致性指标（Judges vs Fans）
| Metric | Value |
| :-- | --: |
| Sign Agreement | 0.667 |
| Cosine Similarity | 0.0168 |
| Pearson Corr | -0.380 |
| Mean Abs Gap | 0.370 |

**结论：**影响方向仅部分一致（2/3 同号），整体相关性为负，说明评委与观众的“偏好结构明显不同”。

### 5.3 Pro Buff 排名（残差均值）
**Top 3（正向加成）**：
- Ezra Sosa (Apolo Anton Ohno week 9)：0.201
- Daniella Karagach (Rumer Willis week 9)：0.129
- Tyne Stecklein：0.124

**Bottom 3（负向）**：
- Fabian Sanchez：-0.261
- Jan Ravnik：-0.138
- Val Chmerkovskiy：-0.105

> 解释：Pro buff 反映在控制年龄/行业/周序与技术趋势后，职业舞者是否仍带来“额外加成”。

### 5.4 Survival（Cox）核心结论
| Feature | Hazard Ratio | p-value |
| :-- | --: | --: |
| Mean fan share (z) | 0.232 | 6.88e-46 |
| Mean judge score (z) | 0.527 | 3.88e-18 |
| Age (z) | 0.737 | 1.16e-04 |
| Industry: Athlete | 5.251 | 1.85e-07 |
| Industry: Singer | 4.052 | 1.86e-05 |
| Industry: Actor | 2.989 | 3.15e-04 |

**解读：**观众投票与评委评分均显著降低淘汰风险；行业类型对“走多远”存在明显结构性差异。

### 5.5 敏感性分析（Sensitivity）
我们对建模假设做了 5 组变体：`base / no_week / no_trend_cum / no_judge_in_fan / alt_industry`。一致性指标如下（数值来自 `task3_sensitivity_summary.csv`）：

| Variant | Sign Agreement | Cosine | Pearson | Mean Abs Gap |
| :-- | --: | --: | --: | --: |
| base | 0.667 | 0.0168 | -0.380 | 0.370 |
| no_week | 0.750 | 0.271 | -0.104 | 0.358 |
| no_trend_cum | 0.714 | 0.711 | 0.783 | 0.221 |
| no_judge_in_fan | 0.778 | 0.223 | -0.142 | 0.339 |
| alt_industry | 0.750 | 0.0156 | -0.352 | 0.367 |

**结论：**
- 去掉 `trend/cum` 会让 judges vs fans 的方向更接近，但仍存在结构性差异。  
- 不同分组方案下结果方向稳定，说明“评委偏技术、观众偏人气”的结论具备鲁棒性。

## 6. 图表清单（English Figures）
- Judges vs Fans Coefficient Dumbbell: `figures/task3_coef_dumbbell_20260131_164313.png`
- Coefficient Heatmap: `figures/task3_coef_heatmap_20260131_164313.png`
- Effect Gap Bar: `figures/task3_coef_gap_20260131_164313.png`
- Pro Buff Caterpillar: `figures/task3_pro_buff_caterpillar_20260131_164313.png`
- Cox Hazard Ratio Forest: `figures/task3_cox_forest_20260131_164324.png`
- Kaplan-Meier by Fan Share: `figures/task3_km_fanshare_20260131_164324.png`
- Sensitivity Heatmap: `figures/task3_sensitivity_heatmap_20260131_164457.png`

## 7. 输出与记录
- 运行脚本：
  - `src/task3_step1_build_dataset.py`
  - `src/task3_step2_models_plots.py`
  - `src/task3_step3_survival.py`
  - `src/task3_step4_sensitivity.py`
- 主要输出：
  - `data/processed/task3_weekly_model.csv`
  - `data/processed/task3_survival_base.csv`
  - `data/processed/task3_model_coefficients.csv`
  - `data/processed/task3_judge_fan_consistency.csv`
  - `data/processed/task3_pro_buff.csv`
  - `data/processed/task3_cox_summary.csv`
  - `data/processed/task3_sensitivity_summary.csv`
- 运行日志：`outputs/task3/task3_runlog.md`

## 8. 写作提示（Narrative）
- 评委评分更像“技术稳定性函数”（趋势与累积分最强）。
- 观众投票更像“人气与话题函数”（行业 + 年龄 + 赛季后期动员）。
- 二者方向性部分一致，但整体结构明显分化（Consistency 指标显示差异）。
- 生存模型证明：**fan share 是最强的“保命因子”**，其次是评委分。

## 9. 可直接使用的叙事段落（中文草稿）
**评委与观众的“偏好函数”不同**  
基于混合效应模型的系数比较，我们发现评委评分主要由技术稳定性驱动（累积分与进步趋势的系数在 Judges 模型中显著且幅度最大），而观众投票则更受“人气与话题”因素影响（行业类型、年龄与赛季后期周次在 Fans 模型中更突出）。这种结构性差异不仅体现在单个系数方向上，也体现在整体一致性指标上：虽然符号一致比例仍超过 2/3，但余弦相似度与相关系数表明两套偏好方向整体并不一致。

**Pro Buff 的含义**  
在控制明星特征与周内表现后，我们用残差均值构建了“Pro Buff”指数，衡量职业舞者对搭档的额外加成。该指标可以被解释为“在同等明星特征下，某些职业舞者带来的稳定增益”，为节目的搭档设计提供了可操作依据。

**走多远：生存视角的结论**  
生存模型结果显示，观众投票份额和评委评分均能显著降低淘汰风险，其中 fan share 的效应更为强烈。这说明在实际赛季中，“人气保护”是决定性因素，而评委评分更多影响技术路线的上升速度与稳定性。
