# 2026 MCM C 题：Data With The Stars（整合写作稿）

> 本文件为整合版写作稿（Summary Sheet + Memo + 主文稿骨架）。
> 任务结果分别来自 Task1/Task2/Task3 的已验证输出。

---

## Summary Sheet（1页摘要）

**问题核心**：在 DWTS 中，观众投票不可观测，但决定淘汰结果。我们反演投票分布，比较规则与机制，并分析职业舞者与明星特征对评分/投票/最终成绩的影响。

**主要发现**
1) **Task1 投票反演可行**：基于 ABC 反演出的后验样本几乎总能重现真实淘汰（整体一致性 0.989），说明投票反演合理。
2) **规则偏向明确**：Percent 规则更偏向人气（FII 高），Rank/Official 更偏向技术保护（TPI 高）。
3) **动态规则会重写赛季**：Frozen 情境下规则差异可控；Dynamic 情境下一致性接近 0，规则改变会改写赛季轨迹。
4) **评委 vs 观众偏好结构不同**：GAM 显示年龄/周次存在非线性，人气效应与技术趋势效应显著分化。
5) **谁能走远**：生存分析（Cox）显示 fan share 是最强“保命因子”，评委分次之。

**建议**
- 若节目目标是“观众参与感”：Percent 更合适；若强调“技术公平/可解释性”：Rank/Official 更合适。
- Judges’ Save 建议采用 Mix 策略（人气与技术折中）。

---

## Memo（1–2页备忘）

**给节目制作方的建议**：
- 规则本身会重塑历史，不只是影响单周淘汰。为了减少“冠军争议”，建议在“技术公平 vs 人气偏向”之间保持可解释的平衡。Mix 策略可以作为稳定选择。
- 观众投票对结果的影响最大（Cox 模型中 HR 最低），说明节目应维持投票机制以保持参与感。
- 职业舞者的整体方差贡献较小，但个别 pro 仍表现出稳定加成，可用于搭档策略优化。

---

## 1. Problem Restatement
- Task1：在评委分数可见、观众投票未知的情况下反演投票份额，并给出一致性与确定性指标。
- Task2：基于反演投票模拟不同规则，量化规则偏向与反事实后果。
- Task3：分析职业舞者与明星特征对评分/投票/生存表现的影响，回答“谁能走远”。

---

## 2. Data & Preprocessing
- 原始数据：`data/raw/C题数据.csv`
- 周度长表：`data/processed/dwts_weekly_long.csv`
- 投票后验：`data/processed/abc_weekly_posterior.csv`

关键处理：
- 仅保留 `active_in_week = True`
- 周内评委分标准化 `judge_z`
- 行业合并：Actor / Singer / Athlete / Reality-TV / Other
- 动态特征：`trend`、`cumulative`

---

## 3. Methods

### 3.1 Task1：ABC 反演投票
- 假设投票份额服从 Dirichlet 先验
- ABC 按真实淘汰结果筛选样本
- 输出：后验均值/方差 + 一致性/确定性

一致性与确定性指标：
- Posterior Consistency（重现真实淘汰）
- Acceptance Rate（解释力）
- Certainty（posterior SD 逆度量）

### 3.2 Task2：规则反事实模拟
- 规则：Rank / Percent / Official Points
- Judges’ Save：Merit / Fan / Mix
- Frozen vs Dynamic：对比规则改变对赛季轨迹的影响
- 指标：FII、TPI、Kendall’s Tau、Consistency

### 3.3 Task3：GAM + Cox（层层迭代）
**Step 1 机制探究（GAM）**
```
judge_z ~ s(age) + s(week) + trend_z + cum_z + industry + is_us + pro + season
fan_logit ~ s(age) + s(week) + trend_z + cum_z + industry + is_us + pro + season + judge_z
```
- 采用 pyGAM，s() 捕捉非线性，f() 处理因子
- fan share 通过 logit 变换

**Step 2 效应归因（Pro Buff）**
- pro 因子系数直接解释为“职业舞者附加效应”

**Step 3 终局预测（Cox）**
```
duration ~ age_z + age_z2 + mean_judge_z + mean_fan_share_z + pro_effect_z + industry + is_us
```
- 处理删失数据（冠军未淘汰）

---

## 4. Results

### 4.1 Task1 核心结果
- Posterior Consistency：0.989
- 平均 Acceptance Rate：0.327
- Rank vs Percent：Percent 一致性更高（0.980 vs 0.841）

关键图表：
- `figures/acceptance_rate_heatmap_*.png`
- `figures/consistency_by_season_*.png`

### 4.2 Task2 核心结果
**Frozen 规则对比**
- Percent：Consistency 0.712 / FII 0.804 / TPI 0.582
- Rank：Consistency 0.660 / FII 0.658 / TPI 0.776

**Dynamic 反事实**
- 一致性接近 0，规则改变会重写赛季轨迹

关键图表：
- `figures/task2_rule_bias_radar_*.png`
- `figures/task2_policy_scorecard_*.png`

### 4.3 Task3 核心结果（v3）
**一致性指标**
- Sign Agreement：0.429
- Cosine Similarity：-0.132
- Pearson Corr：-0.370

**非线性一致性**
- Age 曲线相关：0.943
- Week 曲线相关：-0.997

**Cox 结果**
- fan share HR = 0.227（最强保命因子）
- judge score HR = 0.525

关键图表：
- `figures/task3_smooth_effects_v3_20260131_174512.png`
- `figures/task3_cox_forest_v3_20260131_174526.png`

---

## 5. Recommendations
- **机制建议**：Percent 规则更能体现观众偏好，但会削弱技术保护。
- **治理建议**：Rank/Official 更稳定、可解释性更强，适合作为主规则。
- **折中方案**：Judges’ Save 建议使用 Mix 策略。

---

## 6. Limitations
- fan share 为后验估计而非真实投票。
- GAM 中 pro/season 为因子项而非随机效应。
- Dynamic 反事实对重分配假设敏感。

---

## 7. Reproducibility
- 主要脚本：`src/`
- 结果与日志：`outputs/`
- 图表：`figures/`
- 口径记录：`DECISIONS.md`

---

## AI 使用说明（占位）
> 本报告使用 AI 工具进行代码生成、整理与写作润色，详细记录可附于提交材料。
