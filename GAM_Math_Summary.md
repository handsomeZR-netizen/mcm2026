# GAM数学公式补充完成

**文件**: `paper/Task3_GAM_Mathematical_Details.md`  
**完成时间**: 2026-02-01

---

## ✅ 已完成

创建了完整的GAM建模数学推导文档，包含：

### 1. 基本框架（第1节）
- GAM的一般形式
- 与GLM的关系
- 连接函数和平滑函数

### 2. 评委模型（第2节）
- 完整模型公式（展开形式）
- 变量说明表格
- B-样条基函数的递归定义
- 惩罚项与正则化
- 似然函数
- 最大惩罚似然估计

### 3. 观众模型（第3节）
- logit连接函数
- 完整模型公式
- 逆变换（logit → 概率）
- 二项分布的似然函数
- 最大惩罚似然估计

### 4. 估计算法（第4节）
- IRLS（迭代加权最小二乘）完整步骤
- 工作响应变量的计算
- 权重的计算
- 平滑参数选择（GCV）
- 有效自由度（EDF）

### 5. 模型诊断（第5节）
- 偏差（Deviance）
- AIC
- 系数标准误
- Wald检验
- p值计算

### 6. pyGAM实现（第6节）
- pyGAM的特点
- 模型语法示例
- 拟合与预测代码

### 7. 简化表示（第7节）
- 论文中使用的简洁符号
- 符号说明

### 8. 参考文献（第8节）
- Wood (2017)
- Hastie & Tibshirani (1990)
- 等

---

## 📊 关键公式

### GAM一般形式
$$
g(\mu_i) = \beta_0 + \sum_{j=1}^{p} f_j(x_{ij})
$$

### 评委模型（完整）
$$
\begin{aligned}
\mathbb{E}[\mathrm{judge}_{z,i}] = \mu_i &= \beta_0 + f_1(\mathrm{age}_i) + f_2(\mathrm{week}_i) \\
&\quad + \beta_3 \mathrm{trend}_{z,i} + \beta_4 \mathrm{cum}_{z,i} \\
&\quad + \sum_{k} \beta_{5k} \mathbb{I}(\mathrm{industry}_i = k) \\
&\quad + \beta_6 \mathrm{is}_{\mathrm{US},i} \\
&\quad + \sum_{p} \beta_{7p} \mathbb{I}(\mathrm{pro}_i = p) \\
&\quad + \sum_{s} \beta_{8s} \mathbb{I}(\mathrm{season}_i = s)
\end{aligned}
$$

### 观众模型（完整）
$$
\begin{aligned}
\operatorname{logit}(\mathbb{E}[V_i]) = \eta_i &= \beta_0 + f_1(\mathrm{age}_i) + f_2(\mathrm{week}_i) \\
&\quad + \beta_3 \mathrm{trend}_{z,i} + \beta_4 \mathrm{cum}_{z,i} \\
&\quad + \sum_{k} \beta_{5k} \mathbb{I}(\mathrm{industry}_i = k) \\
&\quad + \beta_6 \mathrm{is}_{\mathrm{US},i} \\
&\quad + \sum_{p} \beta_{7p} \mathbb{I}(\mathrm{pro}_i = p) \\
&\quad + \sum_{s} \beta_{8s} \mathbb{I}(\mathrm{season}_i = s) \\
&\quad + \beta_9 \mathrm{judge}_{z,i}
\end{aligned}
$$

### B-样条基函数
$$
f_j(x) = \sum_{k=1}^{K_j} \beta_{jk} B_{jk}(x)
$$

### 惩罚项
$$
\mathcal{L}(\boldsymbol{\beta}) = -\log L(\boldsymbol{\beta}) + \sum_{j=1}^{p} \lambda_j \int [f_j''(x)]^2 dx
$$

### IRLS算法
1. 工作响应变量：$z_i^{(t)} = \eta_i^{(t)} + (y_i - \mu_i^{(t)}) \left(\frac{d\eta}{d\mu}\right)_{\mu=\mu_i^{(t)}}$
2. 权重：$w_i^{(t)} = \left[\left(\frac{d\mu}{d\eta}\right)_{\eta=\eta_i^{(t)}}\right]^2 / \text{Var}(y_i)$
3. 加权最小二乘：$\hat{\boldsymbol{\beta}}^{(t+1)} = \arg\min \left\{ \sum w_i (z_i - \eta_i)^2 + \text{penalties} \right\}$

---

## 🎯 使用建议

### 选项1：作为附录
将 `Task3_GAM_Mathematical_Details.md` 作为论文附录，标题为：
> **Appendix A: Mathematical Details of GAM Modeling**

### 选项2：整合到正文
将关键公式（第2-3节）整合到论文12.2节，其余作为附录。

### 选项3：在线补充材料
作为在线补充材料（Online Supplementary Material），在论文中引用：
> "Complete mathematical derivations are provided in the Online Supplementary Material."

---

## 📝 论文中的引用方式

### 当前简化版本（论文12.2节）
```markdown
评委模型：
$$
\mathrm{judge}_{z} \sim s(\mathrm{age}) + s(\mathrm{week}) + \mathrm{trend}_{z} + \mathrm{cum}_{z} + \mathrm{industry} + \mathrm{is}_{\mathrm{US}} + \mathrm{pro} + \mathrm{season}
$$

观众模型：
$$
\operatorname{logit}(V) \sim s(\mathrm{age}) + s(\mathrm{week}) + \mathrm{trend}_{z} + \mathrm{cum}_{z} + \mathrm{industry} + \mathrm{is}_{\mathrm{US}} + \mathrm{pro} + \mathrm{season} + \mathrm{judge}_{z}
$$
```

### 建议添加的引用
```markdown
其中 $s(\cdot)$ 表示平滑函数（smooth function），使用B-样条基函数实现，
通过惩罚最大似然估计（penalized maximum likelihood）拟合。
完整的数学推导见附录A。
```

---

## 💡 关键亮点

### 1. 完整性
- 从基本定义到估计算法
- 从理论推导到实现细节
- 涵盖所有关键步骤

### 2. 可读性
- 分节清晰
- 公式编号
- 变量说明表格
- 代码示例

### 3. 严谨性
- 数学符号规范
- 推导步骤完整
- 引用权威文献

### 4. 实用性
- pyGAM实现细节
- 模型诊断方法
- 参数选择策略

---

## 🔗 相关文件

- **数学推导**：`paper/Task3_GAM_Mathematical_Details.md`（新建）
- **总文档**：`paper/Report_Q1-4_Enhanced_zh.md`（12.2节）
- **代码实现**：`src/task3_step2_models_plots.py`

---

## 🚀 下一步

### 如果要整合到论文

1. **决定位置**
   - 附录A？
   - 正文12.2节扩展？
   - 在线补充材料？

2. **添加引用**
   - 在12.2节添加："完整推导见附录A"
   - 或："详细数学推导见在线补充材料"

3. **格式调整**
   - 确保公式编号连续
   - 统一符号使用
   - 检查交叉引用

### 如果作为独立文档

- 已经完成，可以直接使用
- 格式规范，符号清晰
- 可以作为技术报告或补充材料

---

**总结**：GAM建模的完整数学推导已经准备好，包含从基本定义到实现细节的所有内容。你可以根据需要选择整合方式。

---

**版本**: v1.0  
**日期**: 2026-02-01  
**状态**: ✅ 完成
