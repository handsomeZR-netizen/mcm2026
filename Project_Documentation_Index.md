# 项目文档索引

> 2026 MCM C题 - Data With The Stars 项目文档总览

---

## 📚 文档结构

```
项目根目录/
├── 📋 项目概况
│   ├── README.md - 项目总览
│   ├── C题.md - 题目描述（中文）
│   ├── AGENT.md - 团队口径标准
│   └── DECISIONS.md - 决策记录
│
├── 📊 任务一：观众投票反演
│   └── （暂无独立总结文档，内容在paper/中）
│
├── 📊 任务二：规则对比分析
│   ├── Task2_Summary.md - 完整总结（通俗易懂版）
│   └── Task2_Summary.pdf - PDF版本
│
├── 📊 任务三：影响因素分析
│   ├── Task3_Summary.md - 完整总结
│   ├── Task3_Summary.pdf - PDF版本
│   ├── Task3_README.md - 快速入门
│   ├── Task3_Quick_Reference.md - 快速参考
│   ├── Task3_Methodological_Defense.md - 方法论证
│   ├── Task3_O_Prize_Enhancements.md - O奖优化
│   └── Task3_VERSIONS.md - 版本说明
│
├── 📊 任务四：新规则提案
│   ├── Task4_Summary.md - 完整总结（通俗易懂版）
│   ├── Task4_Summary.pdf - PDF版本
│   ├── Task4_README.md - 文档说明
│   └── Task4_Quick_Reference.md - 快速参考
│
└── 📝 论文与报告
    ├── paper/Report_Q1-4_Enhanced_zh.md - 完整报告
    ├── paper/Report_Q1-4_Enhanced_zh.pdf - PDF版本
    ├── paper/Task1.md - 任务一论文
    ├── paper/Task2.md - 任务二论文
    ├── paper/Task3.md - 任务三论文
    └── paper/Task2_Methodological_Defense.md - 任务二方法论证
```

---

## 🎯 快速导航

### 如果你想...

#### 了解项目整体情况
→ 阅读 `README.md`

#### 了解题目要求
→ 阅读 `C题.md`

#### 了解团队口径和决策
→ 阅读 `AGENT.md` 和 `DECISIONS.md`

#### 了解任务一（观众投票反演）
→ 阅读 `paper/Task1.md` 或 `paper/Report_Q1-4_Enhanced_zh.md` 的任务一部分

#### 了解任务二（规则对比分析）
→ 阅读 `Task2_Summary.md`（通俗易懂版）或 `paper/Task2.md`（学术版）

#### 了解任务三（影响因素分析）
→ 阅读 `Task3_Summary.md`（通俗易懂版）或 `paper/Task3.md`（学术版）

#### 了解任务四（新规则提案）
→ 阅读 `Task4_Summary.md`（通俗易懂版）或 `paper/Report_Q1-4_Enhanced_zh.md` 的任务四部分

#### 快速查看某个任务的核心信息
→ 阅读对应的 `Quick_Reference.md` 文件

#### 了解方法论的详细论证
→ 阅读对应的 `Methodological_Defense.md` 文件

#### 写论文
→ 参考 `paper/` 文件夹中的文档和各任务的"写作建议"部分

---

## 📊 各任务核心内容

### 任务一：观众投票反演

**目标**：估算每周每位选手的观众投票数

**方法**：
- ABC（近似贝叶斯计算）
- Dirichlet先验
- 规则约束

**核心指标**：
- Consistency（一致性）
- Certainty（确定性）
- Acceptance Rate（接受率）

**关键发现**：
- 98.9%的周次存在满足规则约束的投票分布
- 不同选手/周的确定性差异显著
- 争议选手（如Bobby Bones）的投票分布更分散

---

### 任务二：规则对比分析

**目标**：比较三种规则（Rank、Percent、Official）的差异

**方法**：
- 反事实模拟（Frozen + Dynamic）
- 三维指标体系（Consistency/FII/TPI）
- 争议案例分析

**核心指标**：
- FII（Fan Influence Index）：观众影响力
- TPI（Technical Protection Index）：技术保护
- Consistency：一致性

**关键发现**：
- Percent最偏观众（FII=0.805），技术保护最弱（TPI=0.582）
- Rank/Official技术保护强（TPI=0.776），但观众影响力低
- 动态模式下蝴蝶效应极强（Consistency≈0）

**文档**：
- `Task2_Summary.md` - 25页完整总结，包含所有图表和分析

---

### 任务三：影响因素分析

**目标**：分析职业舞者、选手特征对结果的影响

**方法**：
- 混合效应模型（Judges vs Fans）
- GAM（广义加性模型）
- Cox生存分析

**核心指标**：
- Pro Buff（职业舞者效应）
- Consistency（评委vs观众一致性）
- Hazard Ratio（淘汰风险比）

**关键发现**：
- 观众投票是最强生存因子（HR=0.227）
- 评委和观众在年龄偏好上高度一致（corr=0.943）
- 评委和观众在周次偏好上几乎相反（corr=-0.997）
- "运动员悖论"：人气高但死得快

**文档**：
- `Task3_Summary.md` - 完整总结
- `Task3_Quick_Reference.md` - 快速参考
- `Task3_Methodological_Defense.md` - 方法论证
- `Task3_O_Prize_Enhancements.md` - O奖优化

---

### 任务四：新规则提案

**目标**：设计一个更公平、更平衡、更透明的新规则

**方案**：Adaptive Percent（自适应百分比规则）

**核心理念**：早期更尊重观众，后期更保护技术

**实现方式**：
- 权重随周次线性变化：w_t = 0.45 → 0.55
- 得分 = w_t × judge_pct + (1 - w_t) × fan_pct

**评估结果**：
- FII=0.807（观众影响力高）
- TPI=0.578（技术保护适中）
- Consistency=0.713（与历史匹配度好）

**五大优势**：
1. 平衡性更好
2. 透明度更高
3. 灵活性更强
4. 争议更少
5. 易于实施

**文档**：
- `Task4_Summary.md` - 25页完整总结，包含所有细节
- `Task4_Quick_Reference.md` - 一页纸快速参考
- `Task4_README.md` - 文档说明

---

## 📈 图表索引

所有图表都在 `figures/` 文件夹中，按任务分类：

### 任务一图表
- `acceptance_rate_*.png` - 接受率分析
- `certainty_*.png` - 确定性分析
- `consistency_*.png` - 一致性分析
- `controversy_*.png` - 争议分析
- `sensitivity_*.png` - 敏感性分析

### 任务二图表
- `task2_rule_bias_radar_*.png` - 规则偏向雷达图
- `task2_kendall_tau_heatmap_*.png` - 规则差异热力图
- `task2_survival_heatmap_*.png` - 生存概率热力图
- `task2_cases_survival_*.png` - 争议案例生存曲线
- `task2_consistency_bar_*.png` - 一致性柱状图
- `task2_policy_frontier_*.png` - 政策前沿图
- `task2_policy_scorecard_*.png` - 政策记分卡
- `task2_storyline_*.png` - 故事线图

### 任务三图表
- `task3_coef_*.png` - 系数分析图
- `task3_cox_forest_*.png` - Cox森林图
- `task3_km_fanshare_*.png` - KM生存曲线
- `task3_pro_buff_*.png` - Pro Buff分析
- `task3_sensitivity_*.png` - 敏感性分析
- `task3_smooth_effects_*.png` - 平滑效应图

### 任务四图表
- `task4_adaptive_scorecard_*.png` - 政策记分卡

---

## 💻 代码索引

所有代码都在 `src/` 文件夹中：

### 数据预处理
- `preprocess_dwts.py` - 数据清洗
- `dwts_rules.py` - 规则引擎

### 任务一
- `step1_build_groundtruth.py` - 构建真实淘汰表
- `step2_rules_smoketest.py` - 规则引擎测试
- `step3_build_priors.py` - 构建先验
- `step4_abc_pilot.py` - ABC试跑
- `step5_abc_batch.py` - ABC批量运行
- `step6_metrics_plots.py` - 指标计算和图表
- `step7_sensitivity_and_cases.py` - 敏感性和案例分析
- `step8_enhanced_plots.py` - 增强图表
- `step9_final_enhancements.py` - 最终优化

### 任务二
- `task2_step1_simulation.py` - 冻结历史模拟
- `task2_step2_metrics_plots.py` - 指标计算和图表
- `task2_step3_dynamic.py` - 动态历史模拟
- `task2_step3_policy_scorecard.py` - 政策记分卡
- `task2_step3_postprocess.py` - 后处理
- `task2_step3_storyline_custom.py` - 故事线图

### 任务三
- `task3_step1_build_dataset.py` - 构建数据集
- `task3_step2_models_plots.py` - 模型和图表
- `task3_step3_survival.py` - 生存分析
- `task3_step4_sensitivity.py` - 敏感性分析
- `task3_enhanced_plots.py` - 增强图表
- `task3_plot_style.py` - 绘图样式

### 任务四
- 任务四的代码已集成到任务二的脚本中
- 核心函数在 `dwts_rules.py` 中

---

## 📊 数据索引

所有数据都在 `data/` 文件夹中：

### 原始数据
- `data/raw/C题数据.csv` - 原始数据

### 处理后数据
- `data/processed/dwts_weekly_long.csv` - 周粒度长表
- `data/processed/dwts_wide_clean.csv` - 宽表
- `data/processed/season_week_truth.csv` - 真实淘汰表
- `data/processed/abc_weekly_posterior.csv` - 观众投票后验分布
- `data/processed/task2_*.csv` - 任务二结果
- `data/processed/task3_*.csv` - 任务三结果

---

## 🎓 学习路径

### 新成员入门
1. 阅读 `README.md` 了解项目概况
2. 阅读 `C题.md` 了解题目要求
3. 阅读 `AGENT.md` 了解团队口径
4. 按顺序阅读各任务的 `Quick_Reference.md`

### 论文写作者
1. 阅读各任务的 `Summary.md` 了解完整内容
2. 阅读 `paper/` 文件夹中的学术版本
3. 参考各任务的"写作建议"部分
4. 查看 `figures/` 文件夹中的图表

### 代码实现者
1. 阅读 `DECISIONS.md` 了解技术决策
2. 查看 `src/` 文件夹中的代码
3. 阅读各任务 `Summary.md` 中的"技术实现"部分
4. 参考代码注释和函数文档

### 方法论研究者
1. 阅读各任务的 `Methodological_Defense.md`
2. 查看 `DECISIONS.md` 中的方法论决策
3. 阅读 `paper/` 文件夹中的学术版本
4. 参考相关文献

---

## ⚠️ 重要提示

1. **文档版本**：所有文档都标注了版本号和更新日期，请注意查看
2. **图表时间戳**：图表文件名包含时间戳，最新的图表时间戳最大
3. **代码依赖**：任务四依赖任务二，任务二依赖任务一
4. **数据流向**：任务一 → 任务二 → 任务四，任务一 → 任务三

---

## 📧 联系方式

如有任何问题或建议，请联系建模团队。

---

**索引版本**：v1.0  
**更新日期**：2026-01-31  
**维护者**：建模团队
