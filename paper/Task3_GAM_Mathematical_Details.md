# Task 3 GAM建模：完整数学推导

> 本文档提供 Task 3 中 GAM（广义加性模型）建模的完整数学推导过程，可作为论文附录或补充材料。

---

## 1. 广义加性模型（GAM）的基本框架

### 1.1 定义

GAM 是广义线性模型（GLM）的扩展，允许响应变量与预测变量之间存在非线性关系。其一般形式为：

$$
g(\mu_i) = \beta_0 + \sum_{j=1}^{p} f_j(x_{ij})
$$

其中：
- $\mu_i = \mathbb{E}[Y_i]$ 是响应变量的期望
- $g(\cdot)$ 是连接函数（link function）
- $f_j(\cdot)$ 是平滑函数（smooth functions），通常用样条（splines）实现
- $x_{ij}$ 是第 $i$ 个观测的第 $j$ 个预测变量

### 1.2 与GLM的关系

GLM 假设线性关系：$g(\mu_i) = \beta_0 + \sum_{j=1}^{p} \beta_j x_{ij}$

GAM 放松了线性假设：$g(\mu_i) = \beta_0 + \sum_{j=1}^{p} f_j(x_{ij})$

当 $f_j(x) = \beta_j x$ 时，GAM 退化为 GLM。

---

## 2. 评委模型（Judge Model）

### 2.1 模型设定

**响应变量**：标准化评委分数 $\mathrm{judge}_{z}$（连续变量）

**分布假设**：高斯分布（正态分布）

$$
\mathrm{judge}_{z,i} \sim \mathcal{N}(\mu_i, \sigma^2)
$$

**连接函数**：恒等连接（identity link）

$$
g(\mu) = \mu
$$

### 2.2 完整模型公式

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

### 2.3 变量说明

| 变量 | 类型 | 说明 |
|------|------|------|
| $f_1(\mathrm{age})$ | 平滑函数 | 年龄的非线性效应 |
| $f_2(\mathrm{week})$ | 平滑函数 | 周次的非线性效应（赛季内时间趋势） |
| $\mathrm{trend}_{z}$ | 连续变量 | 标准化的评委分数趋势（累积变化率） |
| $\mathrm{cum}_{z}$ | 连续变量 | 标准化的累积评委分数 |
| $\mathrm{industry}$ | 因子变量 | 选手行业类别（Athlete, Singer, Actor, Reality-TV等） |
| $\mathrm{is}_{\mathrm{US}}$ | 二元变量 | 是否美国选手（1=是，0=否） |
| $\mathrm{pro}$ | 因子变量 | 职业舞者固定效应 |
| $\mathrm{season}$ | 因子变量 | 赛季固定效应 |

### 2.4 平滑函数的实现

使用 **B-样条基函数**（B-spline basis）：

$$
f_j(x) = \sum_{k=1}^{K_j} \beta_{jk} B_{jk}(x)
$$

其中：
- $B_{jk}(x)$ 是第 $k$ 个 B-样条基函数
- $K_j$ 是基函数的数量（由自由度控制）
- $\beta_{jk}$ 是待估计的系数

**B-样条的递归定义**：

$$
B_{i,0}(x) = \begin{cases}
1 & \text{if } t_i \leq x < t_{i+1} \\
0 & \text{otherwise}
\end{cases}
$$

$$
B_{i,p}(x) = \frac{x - t_i}{t_{i+p} - t_i} B_{i,p-1}(x) + \frac{t_{i+p+1} - x}{t_{i+p+1} - t_{i+1}} B_{i+1,p-1}(x)
$$

其中 $t_i$ 是节点（knots），$p$ 是样条的阶数。

### 2.5 惩罚项与正则化

为避免过拟合，GAM 引入**惩罚项**：

$$
\mathcal{L}(\boldsymbol{\beta}) = -\log L(\boldsymbol{\beta}) + \sum_{j=1}^{p} \lambda_j \int [f_j''(x)]^2 dx
$$

其中：
- $L(\boldsymbol{\beta})$ 是似然函数
- $\lambda_j$ 是平滑参数（smoothing parameter）
- $\int [f_j''(x)]^2 dx$ 是二阶导数的积分，惩罚曲线的"弯曲度"（wiggliness）

**直观解释**：
- $\lambda_j = 0$：无惩罚，可能过拟合
- $\lambda_j \to \infty$：强惩罚，退化为线性函数
- 最优 $\lambda_j$：通过交叉验证或 GCV 选择

### 2.6 似然函数

对于高斯分布：

$$
L(\boldsymbol{\beta}, \sigma^2) = \prod_{i=1}^{n} \frac{1}{\sqrt{2\pi\sigma^2}} \exp\left(-\frac{(y_i - \mu_i)^2}{2\sigma^2}\right)
$$

对数似然：

$$
\log L(\boldsymbol{\beta}, \sigma^2) = -\frac{n}{2}\log(2\pi\sigma^2) - \frac{1}{2\sigma^2} \sum_{i=1}^{n} (y_i - \mu_i)^2
$$

### 2.7 最大惩罚似然估计

$$
\hat{\boldsymbol{\beta}} = \arg\max_{\boldsymbol{\beta}} \left\{ -\frac{1}{2\sigma^2} \sum_{i=1}^{n} (y_i - \mu_i)^2 - \sum_{j=1}^{p} \lambda_j \int [f_j''(x)]^2 dx \right\}
$$

等价于最小化：

$$
\hat{\boldsymbol{\beta}} = \arg\min_{\boldsymbol{\beta}} \left\{ \sum_{i=1}^{n} (y_i - \mu_i)^2 + \sum_{j=1}^{p} \lambda_j \boldsymbol{\beta}_j^T \mathbf{S}_j \boldsymbol{\beta}_j \right\}
$$

其中 $\mathbf{S}_j$ 是惩罚矩阵（penalty matrix）。

---

## 3. 观众模型（Fan Model）

### 3.1 模型设定

**响应变量**：观众投票份额 $V \in (0,1)$（比例数据）

**分布假设**：二项分布（Binomial distribution）或准二项分布（Quasi-binomial）

$$
V_i \sim \text{Binomial}(n_i, p_i)
$$

其中 $n_i$ 是总投票数，$p_i$ 是该选手获得投票的概率。

**连接函数**：logit 连接

$$
g(p) = \operatorname{logit}(p) = \log\frac{p}{1-p}
$$

### 3.2 完整模型公式

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

**关键差异**：
- 观众模型额外包含 $\mathrm{judge}_{z}$（标准化评委分数）作为预测变量
- 使用 logit 连接函数处理 $(0,1)$ 区间的响应变量

### 3.3 逆变换

从 logit 空间转换回概率空间：

$$
\mathbb{E}[V_i] = p_i = \frac{\exp(\eta_i)}{1 + \exp(\eta_i)} = \frac{1}{1 + \exp(-\eta_i)}
$$

其中 $\eta_i$ 是线性预测器（linear predictor）。

### 3.4 似然函数

对于二项分布：

$$
L(\boldsymbol{\beta}) = \prod_{i=1}^{n} \binom{n_i}{y_i} p_i^{y_i} (1-p_i)^{n_i - y_i}
$$

对数似然（忽略常数项）：

$$
\log L(\boldsymbol{\beta}) = \sum_{i=1}^{n} [y_i \log(p_i) + (n_i - y_i) \log(1-p_i)]
$$

用 logit 表示：

$$
\log L(\boldsymbol{\beta}) = \sum_{i=1}^{n} [y_i \eta_i - n_i \log(1 + \exp(\eta_i))]
$$

### 3.5 最大惩罚似然估计

$$
\hat{\boldsymbol{\beta}} = \arg\max_{\boldsymbol{\beta}} \left\{ \sum_{i=1}^{n} [y_i \eta_i - n_i \log(1 + \exp(\eta_i))] - \sum_{j=1}^{p} \lambda_j \int [f_j''(x)]^2 dx \right\}
$$

---

## 4. 模型估计算法

### 4.1 迭代加权最小二乘（IRLS）

GAM 通过 **IRLS 算法**求解，这是 Fisher Scoring 的一个特例。

**算法步骤**：

1. **初始化**：设定初始值 $\mu_i^{(0)}$，通常为 $\mu_i^{(0)} = y_i$

2. **计算工作响应变量**（working response）：

$$
z_i^{(t)} = \eta_i^{(t)} + (y_i - \mu_i^{(t)}) \left(\frac{d\eta}{d\mu}\right)_{\mu=\mu_i^{(t)}}
$$

对于恒等连接：$z_i = \mu_i + (y_i - \mu_i) = y_i$

对于 logit 连接：$z_i = \eta_i + (y_i - \mu_i) / [\mu_i(1-\mu_i)]$

3. **计算权重**（weights）：

$$
w_i^{(t)} = \left[\left(\frac{d\mu}{d\eta}\right)_{\eta=\eta_i^{(t)}}\right]^2 / \text{Var}(y_i)
$$

对于高斯分布：$w_i = 1$

对于二项分布：$w_i = n_i \mu_i (1-\mu_i)$

4. **求解加权最小二乘**：

$$
\hat{\boldsymbol{\beta}}^{(t+1)} = \arg\min_{\boldsymbol{\beta}} \left\{ \sum_{i=1}^{n} w_i^{(t)} (z_i^{(t)} - \eta_i)^2 + \sum_{j=1}^{p} \lambda_j \boldsymbol{\beta}_j^T \mathbf{S}_j \boldsymbol{\beta}_j \right\}
$$

5. **更新**：

$$
\eta_i^{(t+1)} = \mathbf{x}_i^T \hat{\boldsymbol{\beta}}^{(t+1)}
$$

$$
\mu_i^{(t+1)} = g^{-1}(\eta_i^{(t+1)})
$$

6. **收敛检查**：如果 $|\hat{\boldsymbol{\beta}}^{(t+1)} - \hat{\boldsymbol{\beta}}^{(t)}| < \epsilon$，停止；否则返回步骤2

### 4.2 平滑参数选择

**广义交叉验证（GCV）**：

$$
\text{GCV}(\lambda) = \frac{n \sum_{i=1}^{n} (y_i - \hat{y}_i)^2}{(n - \text{EDF})^2}
$$

其中 **有效自由度**（Effective Degrees of Freedom）：

$$
\text{EDF} = \text{tr}(\mathbf{S})
$$

$\mathbf{S}$ 是平滑矩阵（smoother matrix）：

$$
\hat{\mathbf{y}} = \mathbf{S} \mathbf{y}
$$

**最优平滑参数**：

$$
\hat{\lambda} = \arg\min_{\lambda} \text{GCV}(\lambda)
$$

---

## 5. 模型诊断与推断

### 5.1 拟合优度

**偏差（Deviance）**：

$$
D = 2[\log L(\text{saturated model}) - \log L(\text{fitted model})]
$$

对于高斯分布：

$$
D = \sum_{i=1}^{n} (y_i - \hat{\mu}_i)^2
$$

对于二项分布：

$$
D = 2\sum_{i=1}^{n} \left[y_i \log\frac{y_i}{\hat{\mu}_i} + (n_i - y_i) \log\frac{n_i - y_i}{n_i - \hat{\mu}_i}\right]
$$

**AIC（Akaike Information Criterion）**：

$$
\text{AIC} = -2\log L(\hat{\boldsymbol{\beta}}) + 2 \cdot \text{EDF}
$$

### 5.2 系数的标准误

使用 **贝叶斯后验协方差矩阵**近似：

$$
\text{Cov}(\hat{\boldsymbol{\beta}}) \approx (\mathbf{X}^T \mathbf{W} \mathbf{X} + \mathbf{S})^{-1}
$$

其中：
- $\mathbf{X}$ 是设计矩阵
- $\mathbf{W}$ 是权重矩阵（对角矩阵，对角元素为 $w_i$）
- $\mathbf{S}$ 是惩罚矩阵

**标准误**：

$$
\text{SE}(\hat{\beta}_j) = \sqrt{[\text{Cov}(\hat{\boldsymbol{\beta}})]_{jj}}
$$

### 5.3 假设检验

**Wald 检验**：

$$
z = \frac{\hat{\beta}_j}{\text{SE}(\hat{\beta}_j)} \sim \mathcal{N}(0,1)
$$

**p 值**：

$$
p = 2[1 - \Phi(|z|)]
$$

其中 $\Phi(\cdot)$ 是标准正态分布的累积分布函数。

---

## 6. pyGAM 实现细节

### 6.1 pyGAM 的特点

- **无随机效应**：pyGAM 不支持混合效应模型（mixed-effects models）
- **因子项近似**：用固定效应（fixed effects）近似随机效应
- **B-样条基**：默认使用 B-样条基函数
- **自动平滑参数选择**：通过 GCV 或 UBRE 自动选择 $\lambda$

### 6.2 模型语法

```python
from pygam import LinearGAM, LogisticGAM, s, f

# 评委模型（高斯分布）
judge_gam = LinearGAM(
    s(0) +  # age (smooth)
    s(1) +  # week (smooth)
    f(2) +  # trend_z (linear)
    f(3) +  # cum_z (linear)
    f(4) +  # industry (factor)
    f(5) +  # is_US (factor)
    f(6) +  # pro (factor)
    f(7)    # season (factor)
)

# 观众模型（logit连接）
fan_gam = LogisticGAM(
    s(0) +  # age (smooth)
    s(1) +  # week (smooth)
    f(2) +  # trend_z (linear)
    f(3) +  # cum_z (linear)
    f(4) +  # industry (factor)
    f(5) +  # is_US (factor)
    f(6) +  # pro (factor)
    f(7) +  # season (factor)
    f(8)    # judge_z (linear)
)
```

### 6.3 拟合与预测

```python
# 拟合模型
judge_gam.fit(X_train, y_train)

# 预测
y_pred = judge_gam.predict(X_test)

# 获取平滑函数
age_effect = judge_gam.partial_dependence(term=0, X=X_grid)
```

---

## 7. 简化表示（论文中使用）

为简洁起见，我们用以下符号表示完整模型：

**评委模型**：

$$
\mathrm{judge}_{z} \sim s(\mathrm{age}) + s(\mathrm{week}) + \mathrm{trend}_{z} + \mathrm{cum}_{z} + \mathrm{industry} + \mathrm{is}_{\mathrm{US}} + \mathrm{pro} + \mathrm{season}
$$

**观众模型**：

$$
\operatorname{logit}(V) \sim s(\mathrm{age}) + s(\mathrm{week}) + \mathrm{trend}_{z} + \mathrm{cum}_{z} + \mathrm{industry} + \mathrm{is}_{\mathrm{US}} + \mathrm{pro} + \mathrm{season} + \mathrm{judge}_{z}
$$

其中：
- $s(\cdot)$ 表示平滑函数（smooth function）
- $\sim$ 表示"建模为"（modeled as）
- 其他变量表示线性项或因子项

---

## 8. 参考文献

- Wood, S. N. (2017). *Generalized Additive Models: An Introduction with R* (2nd ed.). CRC Press.
- Hastie, T., & Tibshirani, R. (1990). *Generalized Additive Models*. Chapman and Hall/CRC.
- Ruppert, D., Wand, M. P., & Carroll, R. J. (2003). *Semiparametric Regression*. Cambridge University Press.
- de Boor, C. (2001). *A Practical Guide to Splines* (Revised ed.). Springer.

---

**文档版本**: v1.0  
**日期**: 2026-02-01  
**作者**: 建模团队
