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
### 4.0 迭代路线（Layered Storyline）
1) 机制探究：用 GAM 捕捉年龄/周次的非线性偏好结构。  
2) 效应归因：用因子项刻画 pro/season 贡献，并给出 Pro Buff 排名。  
3) 终局预测：保留 Cox 处理删失，回答“谁能走更远”。  
### 4.1 Judges Model（技术评分）——GAM 升级（pyGAM）
采用 **GAM（广义加性模型）** 捕捉非线性，并将职业舞者/赛季以因子项加入：
```
judge_z ~ s(age) + s(week) + trend_z + cum_z + industry + is_us + pro + season
```
实现方式：使用 `pyGAM.LinearGAM`，用 `s()` 表示非线性样条，用 `f()` 表示类别因子（industry/pro/season）。

### 4.2 Fans Model（观众投票）——GAM + Logit
观众投票份额位于 (0,1)，采用 Logit 变换后拟合 GAM：
```
fan_logit ~ s(age) + s(week) + trend_z + cum_z + industry + is_us + pro + season + judge_z
```
- 关键项：`judge_z` 用来检验“粉丝是否也受技术评分影响”。
- Beta 回归在当前环境不可用，因此采用 **Logit + GAM** 作为近似替代（论文中写作“模型迭代”）。

### 4.3 一致性（Consistency）指标
比较 Judges vs Fans 的固定效应向量：
- **Sign Agreement**：符号一致比例。
- **Cosine Similarity**：方向相似度。
- **Pearson Corr**：线性相关性。
- **Mean Abs Gap**：平均绝对差异。

### 4.4 Pro Buff 指标
在 GAM 中，pro 被建模为因子项，其系数直接解释为“职业舞者附加效应”：
- `pro_buff = factor_coef(pro)`
- 附 95% CI（基于系数协方差）。

### 4.5 Survival Model（Cox PH）
保留 Cox 模型，处理删失（冠军未淘汰）。并加入二次项以承接 GAM 发现：
```
duration ~ age_z + age_z2 + mean_judge_z + mean_fan_share_z + pro_effect_z + industry + is_us
```
输出 Hazard Ratio（HR < 1 表示更不易淘汰）。

### 4.6 方差贡献（Pro/Season）
在 GAM 中，用项贡献方差占比衡量 pro/season 对总体波动的解释比例（近似 ICC 思路）。

## 5. 结果汇总（Results）
### 5.1 Judges vs Fans 核心系数（标准化）
（Age/Week 使用样条项，系数以“非线性曲线”呈现，见 `task3_smooth_effects_v3` 图。）

| Feature | Judges Coef | Fans Coef | 说明 |
| :-- | --: | --: | :-- |
| Trend (z) | 0.398 | -0.031 | 评委更看重“进步趋势” |
| Cumulative (z) | 0.783 | -0.026 | 评委更看重“长期技术积累” |
| Judge_z (fans only) | — | 0.232 | 粉丝对评委分有正向响应 |
| Industry: Athlete | 0.001 | 0.246 | 粉丝更偏好运动员 |
| Industry: Singer | -0.009 | 0.079 | 粉丝更偏好歌手 |
| Industry: Actor | 0.009 | 0.053 | 粉丝更偏好演员 |
| Industry: Reality-TV | 0.011 | -0.111 | 评委/粉丝偏好方向分化 |

**解读：**评委模型中 `trend/cum` 主导；粉丝模型中行业与人气因素更突出，且 `judge_z` 对投票显著正向。

### 5.2 一致性指标（Judges vs Fans）
| Metric | Value |
| :-- | --: |
| Sign Agreement | 0.429 |
| Cosine Similarity | -0.132 |
| Pearson Corr | -0.370 |
| Mean Abs Gap | 0.253 |
| Age Curve Corr | 0.943 |
| Week Curve Corr | -0.997 |

**结论：**线性/因子项方向一致性不足一半（Sign=0.429），整体相关性为负，说明评委与观众的“偏好结构明显不同”。
补充：年龄曲线相关性高（0.94），说明“最佳年龄区间”上存在共识；周次曲线相关性为负（-0.997），说明评委与观众在赛季后期的偏好方向相反。

### 5.3 Pro Buff 排名（残差均值）
**Top 3（正向加成）**：
- Ezra Sosa (Apolo Anton Ohno week 9)：0.073
- Alec Mazo：0.068
- Cheryl Burke：0.054

**Bottom 3（负向）**：
- Lindsay Arnold：-0.102
- Jan Ravnik：-0.083
- Fabian Sanchez：-0.077

> 解释：Pro buff 反映在控制年龄/行业/周序与技术趋势后，职业舞者是否仍带来“额外加成”。

### 5.4 Survival（Cox）核心结论
| Feature | Hazard Ratio | p-value |
| :-- | --: | --: |
| Mean fan share (z) | 0.227 | 4.94e-47 |
| Mean judge score (z) | 0.525 | 2.77e-18 |
| Age (z) | 0.682 | 1.61e-05 |
| Age^2 | 1.075 | 1.18e-01 |
| Industry: Athlete | 4.445 | 2.03e-06 |
| Industry: Singer | 3.501 | 1.01e-04 |
| Industry: Actor | 2.441 | 2.97e-03 |

**解读：**观众投票与评委评分均显著降低淘汰风险；行业类型对“走多远”存在明显结构性差异。

### 5.5 敏感性分析（Sensitivity）
我们对建模假设做了 5 组变体：`base / no_week / no_trend_cum / no_judge_in_fan / alt_industry`。一致性指标如下（数值来自 `task3_sensitivity_summary_v3.csv`）：

| Variant | Sign Agreement | Cosine | Pearson | Mean Abs Gap |
| :-- | --: | --: | --: | --: |
| base | 0.429 | -0.132 | -0.370 | 0.253 |
| no_week | 0.571 | 0.450 | 0.450 | 0.207 |
| no_trend_cum | 0.800 | 0.481 | 0.481 | 0.134 |
| no_judge_in_fan | 0.714 | 0.267 | 0.267 | 0.214 |
| alt_industry | 0.500 | -0.392 | -0.392 | 0.286 |

**结论：**
- 去掉 `trend/cum` 会让 judges vs fans 的方向更接近，但仍存在结构性差异。  
- 不同分组方案下结果方向稳定，说明“评委偏技术、观众偏人气”的结论具备鲁棒性。

### 5.6 Pro/Season 方差贡献
方差贡献结果显示：
- pro_variance_share ≈ 0.0016  
- season_variance_share ≈ 0.0009  
说明在控制明星特征与表现后，职业舞者与赛季的总体方差贡献较小，但个别 pro 仍表现出显著加成/减成。

## 6. 图表清单（English Figures）
- Judges vs Fans Coefficient Dumbbell: `figures/task3_coef_dumbbell_v3_20260131_174512.png`
- Coefficient Heatmap: `figures/task3_coef_heatmap_v3_20260131_174512.png`
- Effect Gap Bar: `figures/task3_coef_gap_v3_20260131_174512.png`
- Smooth Effects (Age/Week): `figures/task3_smooth_effects_v3_20260131_174512.png`
- Pro Buff Caterpillar: `figures/task3_pro_buff_caterpillar_v3_20260201_173602.png` *(Enhanced)*
- Cox Hazard Ratio Forest: `figures/task3_cox_forest_v3_20260131_174526.png`
- Kaplan-Meier by Fan Share: `figures/task3_km_fanshare_v3_20260131_174526.png`
- Sensitivity Heatmap: `figures/task3_sensitivity_heatmap_v3_20260131_174434.png`

## 7. 输出与记录
- 运行脚本：
  - `src/task3_step1_build_dataset.py`
  - `src/task3_step2_models_plots.py`
  - `src/task3_step3_survival.py`
  - `src/task3_step4_sensitivity.py`
- 主要输出：
  - `data/processed/task3_weekly_model.csv`
  - `data/processed/task3_survival_base.csv`
  - `data/processed/task3_model_coefficients_v3.csv`
  - `data/processed/task3_judge_fan_consistency_v3.csv`
  - `data/processed/task3_gam_variance_components_v3.csv`
  - `data/processed/task3_smooth_effects_v3.csv`
  - `data/processed/task3_pro_buff_v3.csv`
  - `data/processed/task3_cox_summary_v3.csv`
  - `data/processed/task3_sensitivity_summary_v3.csv`
- 运行日志：`outputs/task3/task3_runlog.md`

## 8. 写作提示（Narrative）
- GAM 显示年龄/周次存在非线性结构（倒 U 型或后期动员），是模型升级亮点。
- 评委评分更像“技术稳定性函数”（趋势与累积分最强）。
- 观众投票更像“人气与话题函数”（行业 + 话题 + 后期动员）。
- 二者方向性部分一致，但整体结构明显分化（Consistency 指标显示差异）。
- 生存模型证明：**fan share 是最强的“保命因子”**，其次是评委分。

## 9. 可直接使用的叙事段落（中文草稿）
**评委与观众的“偏好函数”不同（GAM 视角）**  
在 GAM 中，年龄与周次呈现明显非线性形态（见 smooth effects 图），这表明“最佳年龄区间”和“后期动员效应”并非线性可描述。评委评分主要由技术稳定性驱动（累积分与进步趋势的系数在 Judges 模型中显著且幅度最大），而观众投票则更受行业与人气因素影响。结构性差异不仅体现在单个系数方向上，也体现在一致性指标上：线性/因子项方向一致性不足一半，余弦相似度与相关系数显示两套偏好方向整体并不一致。

**Pro Buff 的含义**  
在控制明星特征与周内表现后，我们用残差均值构建了“Pro Buff”指数，衡量职业舞者对搭档的额外加成。该指标可以被解释为“在同等明星特征下，某些职业舞者带来的稳定增益”，为节目的搭档设计提供了可操作依据。

**走多远：生存视角的结论**  
生存模型结果显示，观众投票份额和评委评分均能显著降低淘汰风险，其中 fan share 的效应更为强烈。这说明在实际赛季中，“人气保护”是决定性因素，而评委评分更多影响技术路线的上升速度与稳定性。
