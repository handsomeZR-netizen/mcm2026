# Judges' Save 对争议明星的影响（论文插入版）

## 反事实分析：如果在争议选手的赛季引入 Judges' Save

我们对四位争议选手（Jerry Rice, Billy Ray Cyrus, Bristol Palin, Bobby Bones）进行了反事实模拟，评估 Judges' Save 机制的影响。

### 核心发现

**Judges' Save 会显著增加人气型选手的淘汰风险。**

| 明星 | 赛季 | 原规则平均风险 | 加入Save后风险 | 风险变化 |
|------|------|----------------|----------------|----------|
| Jerry Rice | S2 | 14.3% | 14.3% | 0% |
| Billy Ray Cyrus | S4 | 14.3% | 28.6% | **+100%** |
| Bristol Palin | S11 | 0% | 11.1% | **+11.1%** |
| Bobby Bones | S27 | 0% | 57.1% | **+57.1%** |

### 可视化

#### 图1：周级淘汰概率对比

![周级淘汰概率对比](figures/judges_save_impact_weekly_20260201_213613.png)

*图 X：四位争议明星在原规则（红色）与加入 Judges' Save 后（绿色）的周级淘汰概率对比。Bobby Bones 在多个周从"零风险"变为"必然淘汰"。*

#### 图2：平均淘汰风险对比

![平均淘汰风险对比](figures/judges_save_impact_summary_20260201_213613.png)

*图 Y：四位争议明星的平均淘汰风险对比。Judges' Save 机制对 Bobby Bones 的影响最为显著（风险从0%增至57.1%）。*

### 机制解释

以 Bobby Bones 为例，在原 Percent 规则下他从未面临淘汰（风险0%），但加入 Judges' Save 后，他在 4 个周会进入 Bottom 2 并被评委淘汰（平均风险57.1%）。

**Judges' Save 创造了"双重筛选"：**

1. **第一关（进入 Bottom 2）**：评委分低的选手容易进入倒数两名
2. **第二关（评委投票）**：评委倾向于救技术好的选手

**示例（Bobby Bones 第4周）：**

```
原规则（Percent）：
  评委分：20/30 = 66.7% → 贡献 33.3%
  观众份额：8.5% → 贡献 4.25%
  综合得分：37.55%（不是最低，安全）✓

加入 Judges' Save：
  第一关：综合得分倒数第二 → 进入 Bottom 2
  第二关：评委分20 vs 对手评委分23 → 被淘汰 ✗
```

### 结论

因此，Judges' Save 机制实际上是**技术导向的规则调整**，而非"公平性"的中立解决方案。从节目运营角度，这可以理解为对"Bobby Bones 争议"的回应——通过增强评委权力来避免类似情况再次发生。

**如果 S27 采用 Judges' Save，Bobby Bones 很可能无法夺冠，甚至难以进入决赛。**

---

## 英文版（English Version）

### Counterfactual Analysis: Impact of Judges' Save on Controversial Celebrities

We conducted counterfactual simulations for four controversial celebrities (Jerry Rice, Billy Ray Cyrus, Bristol Palin, Bobby Bones) to assess the impact of the Judges' Save mechanism.

**Key Finding: Judges' Save significantly increases elimination risk for popularity-driven contestants.**

| Celebrity | Season | Original Risk | With Save | Change |
|-----------|--------|---------------|-----------|--------|
| Jerry Rice | S2 | 14.3% | 14.3% | 0% |
| Billy Ray Cyrus | S4 | 14.3% | 28.6% | **+100%** |
| Bristol Palin | S11 | 0% | 11.1% | **+11.1%** |
| Bobby Bones | S27 | 0% | 57.1% | **+57.1%** |

### Mechanism Explanation

Judges' Save creates a **"double screening"** process:

1. **First Screen (Bottom 2)**: Low judge scores → higher probability of entering Bottom 2
2. **Second Screen (Judges' Vote)**: Judges tend to save technically stronger dancers

**Example (Bobby Bones, Week 4):**

```
Original Rule (Percent):
  Judge score: 20/30 = 66.7% → contributes 33.3%
  Fan share: 8.5% → contributes 4.25%
  Combined: 37.55% (not lowest, safe) ✓

With Judges' Save:
  First screen: Combined score ranks 2nd lowest → enters Bottom 2
  Second screen: Judge score 20 vs opponent 23 → eliminated ✗
```

### Conclusion

Therefore, Judges' Save is a **technique-oriented rule adjustment**, not a neutral "fairness" solution. From a production perspective, this can be understood as a response to the "Bobby Bones controversy"—preventing similar situations by enhancing judges' authority.

**If S27 had used Judges' Save, Bobby Bones would likely not have won the championship, or even reached the finals.**

---

## 数据来源

- 分析脚本：`analyze_judges_save_impact.py`
- 详细结果：`data/processed/judges_save_impact_analysis.csv`
- 完整报告：`Judges_Save_Impact_Analysis.md`

## 可复现性

```bash
conda activate zuoye111
python analyze_judges_save_impact.py
```
