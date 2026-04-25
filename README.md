# Mcm2026

<!-- PORTFOLIO-SNAPSHOT:START -->
<p align="left">
  <img src="https://img.shields.io/badge/category-Research%20and%20academic%20tooling-blue" alt="Category" />
  <img src="https://img.shields.io/badge/status-Public%20portfolio%20artifact-2ea44f" alt="Status" />
</p>

> Mathematical modeling workspace for MCM-style analysis, report drafting, visualization, and reproducible experiment notes.

## Project Snapshot

- Category: Research and academic tooling
- Stack: Python, data-analysis, mathematical-modeling, mcm, python, research-notes
- Status: Public portfolio artifact

## What This Demonstrates

- Presents the project with a clear purpose, technology stack, and review path.
- Emphasizes reproducible research, academic writing, or measurable experiment artifacts.
- Keeps implementation details and usage notes close to the code for easier reuse.

## Quick Start

```bash
Start from README.md
```

<!-- PORTFOLIO-SNAPSHOT:END -->

## Original Documentation

本仓库用于 2026 美赛 C 题建模、分析与写作，目标是**清晰、可复现、可解释**并冲击高分。

---

## 关键文件

- 题目说明：`C题.md` / `C题.pdf`
- 团队口径标准：`AGENT.md`
- 口径变更记录：`DECISIONS.md`
- 原始数据：`data/raw/C题数据.csv`

---

## 题目关键信息（摘要）

- DWTS 1–34 季；每周评委打分 + 观众投票决定淘汰。
- 观众投票未知，需要估计每周/每位选手投票数或份额。
- 规则分段与不确定性：S1–S2 排名法，S3–S27 百分比法，S28–S34 Bottom Two + Judges’ Save（且可能恢复排名法）。
- 交付：≤25 页 PDF + Summary Sheet + 1–2 页备忘录 + 参考文献 + AI 使用报告。

---

## 目录结构

- `data/raw`：原始数据  
- `data/processed`：清洗后的数据  
- `data/external`：外部补充数据与来源  
- `src/`：代码与模型  
- `notebooks/`：探索与可视化  
- `outputs/`：结果表与中间产物  
- `figures/`：图表  
- `paper/`：论文与备忘录  

---

## 快速开始（建议流程）

1. 阅读 `AGENT.md` 对齐口径  
2. 从 `data/raw` 加载数据，完成清洗与特征整理  
3. 建立投票估计模型 + 一致性/确定性指标  
4. 做敏感性分析（排名法 vs 百分比法）  
5. 形成图表与结论，写入 `paper/`
