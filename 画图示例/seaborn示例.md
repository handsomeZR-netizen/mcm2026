# Seaborn 绘图示例库



本文档提供了多个使用 Python Seaborn 库绘制不同类型图表的代码示例。

请使用英文绘图。


## 1. 散点图 (scatterplot)



使用 `scatterplot` 绘制散点图，并根据数据集中的不同变量分配点的颜色和大小。

Python

```
import seaborn as sns
import matplotlib.pyplot as plt
sns.set_theme(style="whitegrid")

# Load the example diamonds dataset
diamonds = sns.load_dataset("diamonds")

# Draw a scatter plot while assigning point colors and sizes to different
# variables in the dataset
f, ax = plt.subplots(figsize=(6.5, 6.5))
sns.despine(f, left=True, bottom=True)
clarity_ranking = ["I1", "SI2", "SI1", "VS2", "VS1", "VVS2", "VVS1", "IF"]
sns.scatterplot(x="carat", y="price",
                hue="clarity", size="depth",
                palette="ch:r=-.2,d=.3_r",
                hue_order=clarity_ranking,
                sizes=(1, 8), linewidth=0,
                data=diamonds, ax=ax)
```



## 2. 折线图 (lineplot)



使用 `lineplot` 绘制长格式（long-form）数据，展示不同事件和区域的响应。

Python

```
import seaborn as sns
sns.set_theme(style="darkgrid")

# Load an example dataset with long-form data
fmri = sns.load_dataset("fmri")

# Plot the responses for different events and regions
sns.lineplot(x="timepoint", y="signal",
             hue="region", style="event",
             data=fmri)
```



## 3. 多面直方图 (displot)



使用 `displot` 绘制直方图，并通过 `col` 和 `row` 参数创建多面网格。

Python

```
import seaborn as sns

sns.set_theme(style="darkgrid")
df = sns.load_dataset("penguins")
sns.displot(
    df, x="flipper_length_mm", col="species", row="sex",
    binwidth=3, height=3, facet_kws=dict(margin_titles=True),
)
```



## 4. 多面关系折线图 (relplot)



使用 `relplot` 并设置 `kind="line"`，在两个子图上绘制折线图。

Python

```
import seaborn as sns
sns.set_theme(style="ticks")

dots = sns.load_dataset("dots")

# Define the palette as a list to specify exact values
palette = sns.color_palette("rocket_r")

# Plot the lines on two facets
sns.relplot(
    data=dots,
    x="time", y="firing_rate",
    hue="coherence", size="choice", col="align",
    kind="line", size_order=["T1", "T2"], palette=palette,
    height=5, aspect=.75, facet_kws=dict(sharex=False),
)
```



## 5. 分类条形图 (catplot)



使用 `catplot` 并设置 `kind="bar"`，按物种和性别绘制嵌套条形图。

Python

```
import seaborn as sns
sns.set_theme(style="whitegrid")

penguins = sns.load_dataset("penguins")

# Draw a nested barplot by species and sex
g = sns.catplot(
    data=penguins, kind="bar",
    x="species", y="body_mass_g", hue="sex",
    errorbar="sd", palette="dark", alpha=.6, height=6
)
g.despine(left=True)
g.set_axis_labels("", "Body mass (g)")
g.legend.set_title("")
```



## 6. 嵌套箱形图 (boxplot)



使用 `boxplot` 绘制嵌套箱形图，按天和时间显示账单。

Python

```
import seaborn as sns
sns.set_theme(style="ticks", palette="pastel")

# Load the example tips dataset
tips = sns.load_dataset("tips")

# Draw a nested boxplot to show bills by day and time
sns.boxplot(x="day", y="total_bill",
            hue="smoker", palette=["m", "g"],
            data=tips)
sns.despine(offset=10, trim=True)
```



## 7. 分裂小提琴图 (violinplot)



使用 `violinplot` 绘制嵌套小提琴图，并使用 `split=True` 分裂小提琴以便于比较。

Python

```
import seaborn as sns
sns.set_theme(style="dark")

# Load the example tips dataset
tips = sns.load_dataset("tips")

# Draw a nested violinplot and split the violins for easier comparison
sns.violinplot(data=tips, x="day", y="total_bill", hue="smoker",
               split=True, inner="quart", fill=False,
               palette={"Yes": "g", "No": ".35"})
```



## 8. 相关矩阵散点图 (relplot)



使用 `relplot` 将相关矩阵绘制为散点图，点的大小和颜色表示相关性。

Python

```
import seaborn as sns
sns.set_theme(style="whitegrid")

# Load the brain networks dataset, select subset, and collapse the multi-index
df = sns.load_dataset("brain_networks", header=[0, 1, 2], index_col=0)

used_networks = [1, 5, 6, 7, 8, 12, 13, 17]
used_columns = (df.columns
                  .get_level_values("network")
                  .astype(int)
                  .isin(used_networks))
df = df.loc[:, used_columns]

df.columns = df.columns.map("-".join)

# Compute a correlation matrix and convert to long-form
corr_mat = df.corr().stack().reset_index(name="correlation")

# Draw each cell as a scatter point with varying size and color
g = sns.relplot(
    data=corr_mat,
    x="level_0", y="level_1", hue="correlation", size="correlation",
    palette="vlag", hue_norm=(-1, 1), edgecolor=".7",
    height=10, sizes=(50, 250), size_norm=(-.2, .8),
)

# Tweak the figure to finalize
g.set(xlabel="", ylabel="", aspect="equal")
g.despine(left=True, bottom=True)
g.ax.margins(.02)
for label in g.ax.get_xticklabels():
    label.set_rotation(90)
```



## 9. 六边形联合图 (jointplot)



使用 `jointplot` 并设置 `kind="hex"`，绘制带有六边形分箱的联合图。

Python

```
import numpy as np
import seaborn as sns
sns.set_theme(style="ticks")

rs = np.random.RandomState(11)
x = rs.gamma(2, size=1000)
y = -.5 * x + rs.normal(size=1000)

sns.jointplot(x=x, y=y, kind="hex", color="#4CB391")
```



## 10. 堆叠直方图 (histplot)



使用 `histplot` 绘制堆叠直方图，并设置 `multiple="stack"` 和对数刻度 `log_scale=True`。

Python

```
import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt

sns.set_theme(style="ticks")

diamonds = sns.load_dataset("diamonds")

f, ax = plt.subplots(figsize=(7, 5))
sns.despine(f)

sns.histplot(
    diamonds,
    x="price", hue="cut",
    multiple="stack",
    palette="light:m_r",
    edgecolor=".3",
    linewidth=.5,
    log_scale=True,
)
ax.xaxis.set_major_formatter(mpl.ticker.ScalarFormatter())
ax.set_xticks([500, 1000, 2000, 5000, 10000])
```



## 11. 箱形图与抖动图 (boxplot & stripplot)



使用 `boxplot` 和 `stripplot` 结合，在箱形图上添加点以显示每个观测值。

Python

```
import seaborn as sns
import matplotlib.pyplot as plt

sns.set_theme(style="ticks")

# Initialize the figure with a logarithmic x axis
f, ax = plt.subplots(figsize=(7, 6))
ax.set_xscale("log")

# Load the example planets dataset
planets = sns.load_dataset("planets")

# Plot the orbital period with horizontal boxes
sns.boxplot(
    planets, x="distance", y="method", hue="method",
    whis=[0, 100], width=.6, palette="vlag"
)

# Add in points to show each observation
sns.stripplot(planets, x="distance", y="method", size=4, color=".3")

# Tweak the visual presentation
ax.xaxis.grid(True)
ax.set(ylabel="")
sns.despine(trim=True, left=True)
```



## 12. 抖动图与点图 (stripplot & pointplot)



使用 `stripplot` 显示每个观测值，并使用 `pointplot` 显示条件均值。

Python

```
import seaborn as sns
import matplotlib.pyplot as plt

sns.set_theme(style="whitegrid")
iris = sns.load_dataset("iris")

# "Melt" the dataset to "long-form" or "tidy" representation
iris = iris.melt(id_vars="species", var_name="measurement")

# Initialize the figure
f, ax = plt.subplots()
sns.despine(bottom=True, left=True)

# Show each observation with a scatterplot
sns.stripplot(
    data=iris, x="value", y="measurement", hue="species",
    dodge=True, alpha=.25, zorder=1, legend=False,
)

# Show the conditional means, aligning each pointplot in the
# center of the strips by adjusting the width allotted to each
# category (.8 by default) by the number of hue levels
sns.pointplot(
    data=iris, x="value", y="measurement", hue="species",
    dodge=.8 - .8 / 3, palette="dark", errorbar=None,
    markers="d", markersize=4, linestyle="none",
)

# Improve the legend
sns.move_legend(
    ax, loc="lower right", ncol=3, frameon=True, columnspacing=1, handletextpad=0,
)
```



## 13. 自定义联合网格 (JointGrid)



使用 `JointGrid` 自定义联合图和边缘图，此处使用 `histplot`。

Python

```
import seaborn as sns
sns.set_theme(style="ticks")

# Load the planets dataset and initialize the figure
planets = sns.load_dataset("planets")
g = sns.JointGrid(data=planets, x="year", y="distance", marginal_ticks=True)

# Set a log scaling on the y axis
g.ax_joint.set(yscale="log")

# Create an inset legend for the histogram colorbar
cax = g.figure.add_axes([.15, .55, .02, .2])

# Add the joint and marginal histogram plots
g.plot_joint(
    sns.histplot, discrete=(True, False),
    cmap="light:#03012d", pmax=.8, cbar=True, cbar_ax=cax
)
g.plot_marginals(sns.histplot, element="step", color="#03012d")
```



## 14. 山脊图 (FacetGrid & kdeplot)



使用 `FacetGrid` 和 `kdeplot` 创建山脊图（Ridgeline plot）。

Python

```
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
sns.set_theme(style="white", rc={"axes.facecolor": (0, 0, 0, 0)})

# Create the data
rs = np.random.RandomState(1979)
x = rs.randn(500)
g = np.tile(list("ABCDEFGHIJ"), 50)
df = pd.DataFrame(dict(x=x, g=g))
m = df.g.map(ord)
df["x"] += m

# Initialize the FacetGrid object
pal = sns.cubehelix_palette(10, rot=-.25, light=.7)
g = sns.FacetGrid(df, row="g", hue="g", aspect=15, height=.5, palette=pal)

# Draw the densities in a few steps
g.map(sns.kdeplot, "x",
      bw_adjust=.5, clip_on=False,
      fill=True, alpha=1, linewidth=1.5)
g.map(sns.kdeplot, "x", clip_on=False, color="w", lw=2, bw_adjust=.5)

# passing color=None to refline() uses the hue mapping
g.refline(y=0, linewidth=2, linestyle="-", color=None, clip_on=False)


# Define and use a simple function to label the plot in axes coordinates
def label(x, color, label):
    ax = plt.gca()
    ax.text(0, .2, label, fontweight="bold", color=color,
            ha="left", va="center", transform=ax.transAxes)


g.map(label, "x")

# Set the subplots to overlap
g.figure.subplots_adjust(hspace=-.25)

# Remove axes details that don't play well with overlap
g.set_titles("")
g.set(yticks=[], ylabel="")
g.despine(bottom=True, left=True)
```



## 15. 组合密度图 (scatterplot, histplot & kdeplot)



在同一张图上组合 `scatterplot`、`histplot` 和 `kdeplot` 来绘制密度等高线。

Python

```
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
sns.set_theme(style="dark")

# Simulate data from a bivariate Gaussian
n = 10000
mean = [0, 0]
cov = [(2, .4), (.4, .2)]
rng = np.random.RandomState(0)
x, y = rng.multivariate_normal(mean, cov, n).T

# Draw a combo histogram and scatterplot with density contours
f, ax = plt.subplots(figsize=(6, 6))
sns.scatterplot(x=x, y=y, s=5, color=".15")
sns.histplot(x=x, y=y, bins=50, pthresh=.1, cmap="mako")
sns.kdeplot(x=x, y=y, levels=5, color="w", linewidths=1)
```



## 16. 填充核密度估计图 (displot)



使用 `displot` 并设置 `kind="kde"` 和 `multiple="fill"` 来绘制填充的核密度估计图。

Python

```
import seaborn as sns
sns.set_theme(style="whitegrid")

# Load the diamonds dataset
diamonds = sns.load_dataset("diamonds")

# Plot the distribution of clarity ratings, conditional on carat
sns.displot(
    data=diamonds,
    x="carat", hue="cut",
    kind="kde", height=6,
    multiple="fill", clip=(0, None),
    palette="ch:rot=-.25,hue=1,light=.75",
)
```



## 17. 线性模型图 (lmplot)



使用 `lmplot` 绘制线性回归模型图，按类别（`hue`）分离。

Python

```
import seaborn as sns
sns.set_theme()

# Load the penguins dataset
penguins = sns.load_dataset("penguins")

# Plot sepal width as a function of sepal_length across days
g = sns.lmplot(
    data=penguins,
    x="bill_length_mm", y="bill_depth_mm", hue="species",
    height=5
)

# Use more informative axis labels than are provided by default
g.set_axis_labels("Snoot length (mm)", "Snoot depth (mm)")
```



## 18. 关系散点图 (relplot)



使用 `relplot` 绘制散点图，其中 `hue` 和 `size` 映射到不同的变量。

Python

```
import seaborn as sns
sns.set_theme(style="white")

# Load the example mpg dataset
mpg = sns.load_dataset("mpg")

# Plot miles per gallon against horsepower with other semantics
sns.relplot(x="horsepower", y="mpg", hue="origin", size="weight",
            sizes=(40, 400), alpha=.5, palette="muted",
            height=6, data=mpg)
```



## 19. 对数尺度关系图 (relplot)



使用 `relplot` 绘制散点图，并设置x轴和y轴为对数尺度（log scale）。

Python

```
import seaborn as sns
sns.set_theme(style="whitegrid")

# Load the example planets dataset
planets = sns.load_dataset("planets")

cmap = sns.cubehelix_palette(rot=-.2, as_cmap=True)
g = sns.relplot(
    data=planets,
    x="distance", y="orbital_period",
    hue="year", size="mass",
    palette=cmap, sizes=(10, 200),
)
g.set(xscale="log", yscale="log")
g.ax.xaxis.grid(True, "minor", linewidth=.25)
g.ax.yaxis.grid(True, "minor", linewidth=.25)
g.despine(left=True, bottom=True)
```



## 20. 热力图 (heatmap)



使用 `heatmap` 绘制热力图，并在单元格中显示数值。

Python

```
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme()

# Load the example flights dataset and convert to long-form
flights_long = sns.load_dataset("flights")
flights = (
    flights_long
    .pivot(index="month", columns="year", values="passengers")
)

# Draw a heatmap with the numeric values in each cell
f, ax = plt.subplots(figsize=(9, 6))
sns.heatmap(flights, annot=True, fmt="d", linewidths=.5, ax=ax)
```



## 21. 时间序列折线图 (lineplot)



使用 `lineplot` 绘制宽格式（wide-form）数据，适用于时间序列数据。

Python

```
import numpy as np
import pandas as pd
import seaborn as sns
sns.set_theme(style="whitegrid")

rs = np.random.RandomState(365)
values = rs.randn(365, 4).cumsum(axis=0)
dates = pd.date_range("1 1 2016", periods=365, freq="D")
data = pd.DataFrame(values, dates, columns=["A", "B", "C", "D"])
data = data.rolling(7).mean()

sns.lineplot(data=data, palette="tab10", linewidth=2.5)
```

------



## 索引 (按函数名首字母排序)



- `boxplot`: [6. 嵌套箱形图](https://www.google.com/search?q=%236-嵌套箱形图-boxplot&authuser=3), [11. 箱形图与抖动图](https://www.google.com/search?q=%2311-箱形图与抖动图-boxplot--stripplot&authuser=3)
- `catplot`: [5. 分类条形图](https://www.google.com/search?q=%235-分类条形图-catplot&authuser=3)
- `displot`: [3. 多面直方图](https://www.google.com/search?q=%233-多面直方图-displot&authuser=3), [16. 填充核密度估计图](https://www.google.com/search?q=%2316-填充核密度估计图-displot&authuser=3)
- `FacetGrid`: [14. 山脊图](https://www.google.com/search?q=%2314-山脊图-facetgrid--kdeplot&authuser=3)
- `heatmap`: [20. 热力图](https://www.google.com/search?q=%2320-热力图-heatmap&authuser=3)
- `histplot`: [10. 堆叠直方图](https://www.google.com/search?q=%2310-堆叠直方图-histplot&authuser=3), [13. 自定义联合网格](https://www.google.com/search?q=%2313-自定义联合网格-jointgrid&authuser=3), [15. 组合密度图](https://www.google.com/search?q=%2315-组合密度图-scatterplot-histplot--kdeplot&authuser=3)
- `JointGrid`: [13. 自定义联合网格](https://www.google.com/search?q=%2313-自定义联合网格-jointgrid&authuser=3)
- `jointplot`: [9. 六边形联合图](https://www.google.com/search?q=%239-六边形联合图-jointplot&authuser=3)
- `kdeplot`: [14. 山脊图](https://www.google.com/search?q=%2314-山脊图-facetgrid--kdeplot&authuser=3), [15. 组合密度图](https://www.google.com/search?q=%2315-组合密度图-scatterplot-histplot--kdeplot&authuser=3)
- `lineplot`: [2. 折线图](https://www.google.com/search?q=%232-折线图-lineplot&authuser=3), [21. 时间序列折线图](https://www.google.com/search?q=%2321-时间序列折线图-lineplot&authuser=3)
- `lmplot`: [17. 线性模型图](https://www.google.com/search?q=%2317-线性模型图-lmplot&authuser=3)
- `pointplot`: [12. 抖动图与点图](https://www.google.com/search?q=%2312-抖动图与点图-stripplot--pointplot&authuser=3)
- `relplot`: [4. 多面关系折线图](https://www.google.com/search?q=%234-多面关系折线图-relplot&authuser=3), [8. 相关矩阵散点图](https://www.google.com/search?q=%238-相关矩阵散点图-relplot&authuser=3), [18. 关系散点图](https://www.google.com/search?q=%2318-关系散点图-relplot&authuser=3), [19. 对数尺度关系图](https://www.google.com/search?q=%2319-对数尺度关系图-relplot&authuser=3)
- `scatterplot`: [1. 散点图](https://www.google.com/search?q=%231-散点图-scatterplot&authuser=3), [15. 组合密度图](https://www.google.com/search?q=%2315-组合密度图-scatterplot-histplot--kdeplot&authuser=3)
- `stripplot`: [11. 箱形图与抖动图](https://www.google.com/search?q=%2311-箱形图与抖动图-boxplot--stripplot&authuser=3), [12. 抖动图与点图](https://www.google.com/search?q=%2312-抖动图与点图-stripplot--pointplot&authuser=3)
- `violinplot`: [7. 分裂小提琴图](https://www.google.com/search?q=%237-分裂小提琴图-violinplot&authuser=3)

