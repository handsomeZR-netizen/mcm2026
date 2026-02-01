# 设计文档：美赛论文可视化优化系统

## 概述

本系统为美赛论文《基于贝叶斯反演的《与星共舞》观众投票重建》提供统一的"论文级"可视化解决方案。系统采用分层架构，包括样式管理层、图表生成层和导出验证层，确保所有图表符合O奖（Outstanding Winner）标准。

核心设计理念：
1. **统一性**：所有图表使用相同的样式配置和配色方案
2. **可配置性**：通过配置文件管理样式参数，无需修改代码
3. **可扩展性**：支持新增图表类型和样式变体
4. **质量保证**：自动验证导出图表的质量指标

系统将重构现有的25+个绘图脚本，建立统一的样式基础设施，并提供高级视觉元素（渐变、水印、专业注释）支持。

## 架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Configuration Layer                       │
│  ┌──────────────────┐         ┌─────────────────────────┐  │
│  │  style_config.   │────────▶│  StyleManager           │  │
│  │  yaml            │         │  - Load config          │  │
│  └──────────────────┘         │  - Apply rcParams       │  │
│                                │  - Manage color palette │  │
│                                └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Visualization Layer                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────┐ │
│  │  PlotGenerator   │  │  AnnotationSystem│  │  Gradient │ │
│  │  - Heatmap       │  │  - Rounded boxes │  │  Manager  │ │
│  │  - Bar chart     │  │  - Arrows        │  │  - Color  │ │
│  │  - Radar chart   │  │  - Smart layout  │  │    ramps  │ │
│  │  - Survival      │  └──────────────────┘  └───────────┘ │
│  │  - Flowchart     │                                        │
│  └──────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Export & Validation Layer                 │
│  ┌──────────────────┐         ┌─────────────────────────┐  │
│  │  FigureExporter  │────────▶│  QualityValidator       │  │
│  │  - PNG (300 DPI) │         │  - Check DPI            │  │
│  │  - PDF/SVG       │         │  - Verify colors        │  │
│  │  - Font embed    │         │  - Validate fonts       │  │
│  └──────────────────┘         │  - Generate report      │  │
│                                └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 数据流

1. **初始化阶段**：StyleManager从配置文件加载样式参数，设置全局matplotlib rcParams
2. **绘图阶段**：PlotGenerator使用统一样式创建图表，AnnotationSystem添加注释元素
3. **导出阶段**：FigureExporter导出多种格式，QualityValidator验证输出质量
4. **迁移阶段**：现有脚本通过适配器模式接入新系统

## 组件和接口

### 1. StyleManager（样式管理器）

**职责**：管理全局绘图样式配置，提供统一的视觉风格。

**接口**：

```python
class StyleManager:
    """
    Manages global plotting styles and configurations.
    All text in plots should be in English.
    """
    
    def __init__(self, config_path: str = "config/style_config.yaml"):
        """Initialize style manager with configuration file."""
        pass
    
    def load_config(self) -> dict:
        """Load style configuration from YAML file."""
        pass
    
    def apply_global_style(self) -> None:
        """Apply global matplotlib rcParams based on configuration."""
        pass
    
    def get_color_palette(self) -> dict[str, str]:
        """
        Get the unified color palette.
        Returns: Dictionary mapping semantic names to hex colors.
        Example: {'primary': '#1f77b4', 'secondary': '#ff7f0e', ...}
        """
        pass
    
    def get_font_config(self) -> dict[str, Any]:
        """
        Get font configuration for different text elements.
        Returns: Dictionary with font families and sizes.
        """
        pass
    
    def validate_config(self) -> list[str]:
        """
        Validate configuration parameters.
        Returns: List of validation warnings/errors.
        """
        pass
```

**配置文件结构**（style_config.yaml）：

```yaml
# Global style configuration for MCM paper visualization
version: "1.0"

# Color palette (maximum 6 colors for academic clarity)
colors:
  primary: "#1f77b4"      # Navy blue - for main data
  secondary: "#ff7f0e"    # Orange - for comparison
  accent: "#2ca02c"       # Green - for highlights
  warning: "#d62728"      # Red - for risks/alerts
  neutral: "#7f7f7f"      # Gray - for reference
  background: "#f7f8fa"   # Light gray - for backgrounds

# Font configuration
fonts:
  family_serif: "Times New Roman"
  family_sans: "Arial"
  size_body: 10
  size_title: 12
  size_label: 11
  size_annotation: 9

# Figure settings
figure:
  dpi: 300
  facecolor: "#ffffff"
  default_width: 8
  default_height: 6

# Line and marker settings
lines:
  linewidth: 1.5
  markersize: 6

# Grid settings
grid:
  alpha: 0.3
  linestyle: "--"
  linewidth: 0.5

# Export settings
export:
  formats: ["png", "pdf", "svg"]
  bbox_inches: "tight"
  transparent: false
```

### 2. PlotGenerator（图表生成器）

**职责**：生成各类专业图表，应用统一样式和高级视觉元素。

**接口**：

```python
class PlotGenerator:
    """
    Generates various types of plots with unified styling.
    All plot labels, titles, and annotations must be in English.
    """
    
    def __init__(self, style_manager: StyleManager):
        """Initialize with style manager."""
        self.style = style_manager
        self.colors = style_manager.get_color_palette()
    
    def create_heatmap(
        self,
        data: np.ndarray,
        row_labels: list[str],
        col_labels: list[str],
        title: str,
        cmap: str = "viridis",
        annotate: bool = True,
        colorbar_label: str = ""
    ) -> plt.Figure:
        """
        Create optimized heatmap with proper spacing and colorbar.
        
        Args:
            data: 2D array of values
            row_labels: Labels for rows (in English)
            col_labels: Labels for columns (in English)
            title: Plot title (in English)
            cmap: Colormap name (perceptually uniform)
            annotate: Whether to show cell values
            colorbar_label: Label for colorbar (in English)
        
        Returns:
            Matplotlib figure object
        """
        pass
    
    def create_bar_chart_with_gradient(
        self,
        categories: list[str],
        values: list[float],
        title: str,
        xlabel: str,
        ylabel: str,
        gradient_colors: tuple[str, str] = None,
        rounded_corners: bool = True
    ) -> plt.Figure:
        """
        Create bar chart with gradient fills and rounded corners.
        All labels must be in English.
        """
        pass
    
    def create_radar_chart(
        self,
        categories: list[str],
        values_dict: dict[str, list[float]],
        title: str,
        fill_alpha: float = 0.25
    ) -> plt.Figure:
        """
        Create radar chart for multi-dimensional comparison.
        All labels must be in English.
        """
        pass
    
    def create_survival_curve(
        self,
        time_points: np.ndarray,
        survival_probs: dict[str, np.ndarray],
        confidence_intervals: dict[str, tuple[np.ndarray, np.ndarray]],
        title: str,
        xlabel: str = "Time",
        ylabel: str = "Survival Probability"
    ) -> plt.Figure:
        """
        Create survival curve with confidence intervals.
        All labels must be in English.
        """
        pass
    
    def create_flowchart(
        self,
        nodes: list[dict],
        edges: list[tuple[str, str, str]],
        title: str,
        layout: str = "hierarchical"
    ) -> plt.Figure:
        """
        Create flowchart with grouped elements and dashed boundaries.
        
        Args:
            nodes: List of node dicts with keys: id, label, type, group
            edges: List of (source_id, target_id, label) tuples
            title: Chart title (in English)
            layout: Layout algorithm ('hierarchical', 'circular', etc.)
        
        All text must be in English.
        """
        pass
```

### 3. AnnotationSystem（注释系统）

**职责**：管理图表中的文字标注、箭头和说明框。

**接口**：

```python
class AnnotationSystem:
    """
    Manages annotations, labels, and callout boxes.
    All annotation text must be in English.
    """
    
    def __init__(self, style_manager: StyleManager):
        """Initialize with style manager."""
        self.style = style_manager
    
    def add_rounded_box(
        self,
        ax: plt.Axes,
        text: str,
        xy: tuple[float, float],
        box_color: str = None,
        alpha: float = 0.8,
        fontsize: int = None
    ) -> None:
        """
        Add rounded annotation box at specified position.
        Text must be in English.
        """
        pass
    
    def add_arrow_annotation(
        self,
        ax: plt.Axes,
        text: str,
        xy: tuple[float, float],
        xytext: tuple[float, float],
        arrow_style: str = "->",
        color: str = None
    ) -> None:
        """
        Add arrow annotation pointing to data point.
        Text must be in English.
        """
        pass
    
    def auto_position_labels(
        self,
        ax: plt.Axes,
        points: list[tuple[float, float]],
        labels: list[str],
        avoid_overlap: bool = True
    ) -> None:
        """
        Automatically position labels to avoid overlaps.
        Labels must be in English.
        """
        pass
```

### 4. GradientManager（渐变管理器）

**职责**：创建和管理颜色渐变效果。

**接口**：

```python
class GradientManager:
    """Manages color gradients for advanced visualizations."""
    
    def create_linear_gradient(
        self,
        color_start: str,
        color_end: str,
        n_steps: int = 256
    ) -> np.ndarray:
        """Create linear gradient between two colors."""
        pass
    
    def apply_gradient_to_bars(
        self,
        ax: plt.Axes,
        bars: list,
        gradient_colors: tuple[str, str]
    ) -> None:
        """Apply gradient fill to bar chart rectangles."""
        pass
    
    def create_radial_gradient(
        self,
        center_color: str,
        edge_color: str,
        size: tuple[int, int]
    ) -> np.ndarray:
        """Create radial gradient for backgrounds."""
        pass
```

### 5. FigureExporter（图表导出器）

**职责**：导出高质量图表文件，支持多种格式。

**接口**：

```python
class FigureExporter:
    """Exports figures in multiple high-quality formats."""
    
    def __init__(self, output_dir: str = "figures/"):
        """Initialize with output directory."""
        self.output_dir = Path(output_dir)
    
    def export_figure(
        self,
        fig: plt.Figure,
        filename: str,
        formats: list[str] = None,
        dpi: int = 300
    ) -> dict[str, Path]:
        """
        Export figure in specified formats.
        
        Args:
            fig: Matplotlib figure object
            filename: Base filename (without extension)
            formats: List of formats ['png', 'pdf', 'svg']
            dpi: Resolution for raster formats
        
        Returns:
            Dictionary mapping format to output file path
        """
        pass
    
    def export_with_watermark(
        self,
        fig: plt.Figure,
        filename: str,
        watermark_text: str,
        position: str = "bottom-right",
        alpha: float = 0.3
    ) -> dict[str, Path]:
        """Export figure with watermark overlay."""
        pass
    
    def batch_export(
        self,
        figures: dict[str, plt.Figure],
        formats: list[str] = None
    ) -> dict[str, dict[str, Path]]:
        """Export multiple figures at once."""
        pass
```

### 6. QualityValidator（质量验证器）

**职责**：验证导出图表是否符合O奖标准。

**接口**：

```python
class QualityValidator:
    """Validates exported figures against O-award standards."""
    
    def __init__(self, style_manager: StyleManager):
        """Initialize with style manager for reference standards."""
        self.style = style_manager
    
    def validate_figure(self, fig_path: Path) -> dict[str, Any]:
        """
        Validate a single figure file.
        
        Returns:
            Dictionary with validation results:
            {
                'dpi': {'value': 300, 'passed': True},
                'colors': {'used': [...], 'passed': True},
                'fonts': {'sizes': [...], 'passed': True},
                'labels': {'has_title': True, 'has_axes_labels': True},
                'overall_score': 95
            }
        """
        pass
    
    def validate_batch(
        self,
        fig_dir: Path
    ) -> pd.DataFrame:
        """
        Validate all figures in directory.
        
        Returns:
            DataFrame with validation results for each figure
        """
        pass
    
    def generate_report(
        self,
        validation_results: dict,
        output_path: Path
    ) -> None:
        """Generate HTML report of validation results."""
        pass
```

### 7. PlotMigrator（图表迁移器）

**职责**：将现有绘图脚本迁移到新样式系统。

**接口**：

```python
class PlotMigrator:
    """Migrates existing plotting scripts to new style system."""
    
    def __init__(
        self,
        style_manager: StyleManager,
        plot_generator: PlotGenerator
    ):
        """Initialize with new system components."""
        self.style = style_manager
        self.generator = plot_generator
    
    def analyze_script(self, script_path: Path) -> dict[str, Any]:
        """
        Analyze existing plotting script.
        
        Returns:
            Dictionary with script analysis:
            {
                'plot_types': ['heatmap', 'bar'],
                'color_usage': [...],
                'font_usage': [...],
                'migration_complexity': 'medium'
            }
        """
        pass
    
    def create_migration_plan(
        self,
        script_path: Path
    ) -> list[dict[str, str]]:
        """
        Create step-by-step migration plan.
        
        Returns:
            List of migration steps with descriptions
        """
        pass
    
    def migrate_script(
        self,
        script_path: Path,
        output_path: Path,
        preserve_data_logic: bool = True
    ) -> None:
        """
        Migrate script to use new style system.
        Preserves all data processing logic.
        """
        pass
```

## 数据模型

### StyleConfig（样式配置）

```python
@dataclass
class StyleConfig:
    """Configuration for visualization styling."""
    
    version: str
    colors: dict[str, str]  # Semantic name -> hex color
    fonts: FontConfig
    figure: FigureConfig
    lines: LineConfig
    grid: GridConfig
    export: ExportConfig
    
    def validate(self) -> list[str]:
        """Validate configuration values."""
        warnings = []
        
        # Check color count
        if len(self.colors) > 6:
            warnings.append("Color palette has more than 6 colors")
        
        # Check DPI
        if self.figure.dpi < 300:
            warnings.append(f"DPI {self.figure.dpi} is below recommended 300")
        
        # Check font sizes
        if self.fonts.size_body < 8 or self.fonts.size_body > 12:
            warnings.append(f"Body font size {self.fonts.size_body} outside recommended range [8-12]")
        
        return warnings

@dataclass
class FontConfig:
    """Font configuration."""
    family_serif: str
    family_sans: str
    size_body: int
    size_title: int
    size_label: int
    size_annotation: int

@dataclass
class FigureConfig:
    """Figure-level configuration."""
    dpi: int
    facecolor: str
    default_width: float
    default_height: float

@dataclass
class LineConfig:
    """Line and marker configuration."""
    linewidth: float
    markersize: float

@dataclass
class GridConfig:
    """Grid styling configuration."""
    alpha: float
    linestyle: str
    linewidth: float

@dataclass
class ExportConfig:
    """Export settings."""
    formats: list[str]
    bbox_inches: str
    transparent: bool
```

### ValidationResult（验证结果）

```python
@dataclass
class ValidationResult:
    """Result of figure quality validation."""
    
    figure_path: Path
    dpi_check: CheckResult
    color_check: CheckResult
    font_check: CheckResult
    label_check: CheckResult
    overall_score: float  # 0-100
    
    def passed(self) -> bool:
        """Check if all validations passed."""
        return all([
            self.dpi_check.passed,
            self.color_check.passed,
            self.font_check.passed,
            self.label_check.passed
        ])

@dataclass
class CheckResult:
    """Result of individual validation check."""
    name: str
    passed: bool
    value: Any
    expected: Any
    message: str
```

### PlotMetadata（图表元数据）

```python
@dataclass
class PlotMetadata:
    """Metadata for generated plots."""
    
    plot_type: str  # 'heatmap', 'bar', 'radar', etc.
    title: str
    created_at: datetime
    source_script: str
    data_shape: tuple[int, ...]
    colors_used: list[str]
    export_formats: list[str]
    validation_score: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'plot_type': self.plot_type,
            'title': self.title,
            'created_at': self.created_at.isoformat(),
            'source_script': self.source_script,
            'data_shape': self.data_shape,
            'colors_used': self.colors_used,
            'export_formats': self.export_formats,
            'validation_score': self.validation_score
        }
```

## 正确性属性

*属性（Property）是系统在所有有效执行中应保持为真的特征或行为——本质上是关于系统应该做什么的形式化陈述。属性是人类可读规范和机器可验证正确性保证之间的桥梁。*

### 属性反思

在分析了60+个验收标准后，我识别出以下冗余模式并进行了合并：

**冗余组1：样式一致性**
- 需求1.5（线宽、标记大小一致性）和需求1.6（自动应用样式）可以合并为一个综合属性：所有图表自动应用统一样式配置
- 需求9.4（注释字体一致性）也属于这个范畴

**冗余组2：配色验证**
- 需求1.2（配色数量限制）、需求2.2（流程图使用统一配色）、需求3.5（柱状图使用统一配色）、需求12.2（验证配色使用）可以合并为：所有图表使用统一配色方案

**冗余组3：导出格式**
- 需求2.6（流程图导出矢量格式）和需求8.1（导出多种格式）可以合并为：所有图表导出多种格式

**冗余组4：注释布局**
- 需求3.4（注释避免重叠数据）、需求9.3（注释自动避免重叠）可以合并为：注释智能布局避免重叠

**冗余组5：视觉简洁性**
- 需求3.6（最小化边框）、需求5.6（移除不必要网格线）可以合并为：最小化视觉杂乱

**冗余组6：迁移保真度**
- 需求10.3（保留数据处理逻辑）和需求10.4（保持数据兼容性）可以合并为：迁移保持功能等价性

经过反思，我将60+个验收标准精简为25个核心属性，每个属性提供独特的验证价值。

### 核心属性列表

**属性1：样式配置加载正确性**
*对于任何*有效的样式配置文件，StyleManager加载后应正确设置所有matplotlib rcParams参数。
**验证需求：1.1, 11.1**

**属性2：配色方案约束**
*对于任何*加载的配色方案，颜色数量应在5-6个范围内，且所有生成的图表只使用这些颜色。
**验证需求：1.2, 2.2, 3.5, 12.2**

**属性3：字体配置一致性**
*对于任何*生成的图表，所有文本元素（标题、标签、注释）的字体族和大小应符合全局配置。
**验证需求：1.3, 9.4**

**属性4：DPI质量保证**
*对于任何*导出的图表文件，DPI应不低于300。
**验证需求：1.4, 12.1**

**属性5：样式自动应用**
*对于任何*通过PlotGenerator创建的图表，应自动应用统一的样式配置（线宽、标记大小、网格样式）。
**验证需求：1.5, 1.6**

**属性6：流程图节点形状规范**
*对于任何*流程图，处理节点应使用圆角矩形，决策节点应使用菱形。
**验证需求：2.3**

**属性7：流程图边标注完整性**
*对于任何*流程图中的边，应包含方向箭头和清晰的标签。
**验证需求：2.4**

**属性8：流程图布局无重叠**
*对于任何*流程图，节点之间应有适当间距，不应出现重叠。
**验证需求：2.5**

**属性9：柱状图渐变效果**
*对于任何*使用渐变选项的柱状图，柱子应使用从配色方案中选择的渐变填充。
**验证需求：3.1**

**属性10：柱状图圆角效果**
*对于任何*柱状图，矩形应具有圆角（当启用该选项时）。
**验证需求：3.2**

**属性11：注释框样式规范**
*对于任何*注释框，应具有圆角、可配置的背景色和半透明效果。
**验证需求：3.3, 9.1**

**属性12：注释智能布局**
*对于任何*包含多个注释的图表，注释应自动调整位置以避免与数据元素或其他注释重叠。
**验证需求：3.4, 9.3**

**属性13：视觉简洁性**
*对于任何*图表，应最小化或移除不必要的边框和网格线，保持视觉简洁。
**验证需求：3.6, 5.6**

**属性14：水印不遮挡数据**
*对于任何*添加了水印的图表，水印区域不应与关键数据区域重叠。
**验证需求：4.4**

**属性15：热力图单元格间距**
*对于任何*热力图，单元格之间应有适当的空白间距。
**验证需求：5.1**

**属性16：热力图色图选择**
*对于任何*热力图，应使用感知均匀的色图（如viridis、plasma）；对于相关矩阵，应使用以零为中心的发散色图。
**验证需求：5.2, 5.5**

**属性17：热力图条件注释**
*对于任何*尺寸小于10x10的热力图，应自动添加单元格数值注释。
**验证需求：5.4**

**属性18：雷达图轴均匀分布**
*对于任何*雷达图，轴应均匀分布，标签应清晰且不重叠。
**验证需求：6.1, 6.5**

**属性19：雷达图多实体区分**
*对于任何*比较多个实体的雷达图，应使用不同的线型和颜色进行区分。
**验证需求：6.4**

**属性20：生存曲线置信区间显示**
*对于任何*生存曲线，置信区间应显示为阴影区域。
**验证需求：7.1**

**属性21：多曲线线型区分**
*对于任何*包含多条曲线的图表，应使用不同的线型（实线、虚线、点线）进行区分。
**验证需求：7.2**

**属性22：导出格式多样性**
*对于任何*图表，应能导出为PNG（300+ DPI）和矢量格式（PDF/SVG）。
**验证需求：2.6, 8.1**

**属性23：导出样式保真度（往返属性）**
*对于任何*图表，导出后重新加载，所有样式元素（字体、颜色、透明度）应保持不变。
**验证需求：8.2**

**属性24：迁移功能等价性**
*对于任何*迁移的绘图脚本，迁移前后使用相同数据应产生相同的数据处理结果（不考虑视觉样式）。
**验证需求：10.3, 10.4**

**属性25：配置验证拒绝无效值**
*对于任何*包含超出允许范围的参数的配置，StyleManager应拒绝加载并生成警告。
**验证需求：11.3, 11.6**

**属性26：质量验证完整性检查**
*对于任何*图表，质量验证器应检查DPI、配色、字体大小、标签完整性，并生成合规分数。
**验证需求：12.1, 12.2, 12.3, 12.4, 12.6**

**属性27：验证失败详细报告**
*对于任何*验证失败的图表，系统应生成包含具体问题的详细报告。
**验证需求：12.5**

## 错误处理

### 错误类型和处理策略

**1. 配置加载错误**
- **场景**：配置文件不存在、格式错误、参数无效
- **处理**：记录错误日志，使用默认配置，向用户显示警告
- **恢复**：提供配置验证工具，帮助用户修复配置

**2. 数据格式错误**
- **场景**：输入数据形状不匹配、包含NaN/Inf值、类型错误
- **处理**：抛出描述性异常，指出具体的数据问题
- **恢复**：提供数据验证函数，在绘图前检查数据

**3. 导出失败**
- **场景**：磁盘空间不足、权限问题、文件被占用
- **处理**：捕获IO异常，记录详细错误信息
- **恢复**：尝试备用导出路径，提示用户检查权限

**4. 样式冲突**
- **场景**：用户代码手动设置了与全局样式冲突的参数
- **处理**：记录警告，优先使用全局样式
- **恢复**：提供样式重置函数

**5. 迁移失败**
- **场景**：无法解析旧脚本、依赖缺失、API不兼容
- **处理**：生成迁移报告，标记失败的部分
- **恢复**：提供手动迁移指南，保留原始脚本

### 错误处理接口

```python
class VisualizationError(Exception):
    """Base exception for visualization system."""
    pass

class ConfigurationError(VisualizationError):
    """Raised when configuration is invalid."""
    pass

class DataValidationError(VisualizationError):
    """Raised when input data is invalid."""
    pass

class ExportError(VisualizationError):
    """Raised when figure export fails."""
    pass

class MigrationError(VisualizationError):
    """Raised when script migration fails."""
    pass

def validate_data_for_heatmap(data: np.ndarray) -> None:
    """
    Validate data before creating heatmap.
    Raises DataValidationError if data is invalid.
    """
    if data.ndim != 2:
        raise DataValidationError(f"Heatmap requires 2D data, got {data.ndim}D")
    
    if np.any(np.isnan(data)):
        raise DataValidationError("Data contains NaN values")
    
    if np.any(np.isinf(data)):
        raise DataValidationError("Data contains infinite values")

def safe_export(
    fig: plt.Figure,
    path: Path,
    fallback_dir: Path = None
) -> Path:
    """
    Safely export figure with fallback handling.
    Returns actual export path.
    """
    try:
        fig.savefig(path)
        return path
    except IOError as e:
        if fallback_dir:
            fallback_path = fallback_dir / path.name
            fig.savefig(fallback_path)
            return fallback_path
        else:
            raise ExportError(f"Failed to export figure: {e}")
```

## 测试策略

### 双重测试方法

本系统采用**单元测试**和**属性测试**相结合的方法，确保全面的质量保证：

- **单元测试**：验证特定示例、边界情况和错误条件
- **属性测试**：验证跨所有输入的通用属性
- 两者互补且都是必需的

### 单元测试重点

单元测试应专注于：
- **具体示例**：展示正确行为的特定案例
- **集成点**：组件之间的交互
- **边界情况**：空数据、单元素数据、极大数据
- **错误条件**：无效输入、配置错误、IO失败

避免编写过多的单元测试——属性测试已经覆盖了大量输入组合。

### 属性测试配置

**测试库选择**：使用Python的`hypothesis`库进行属性测试

**配置要求**：
- 每个属性测试最少运行100次迭代（由于随机化）
- 每个测试必须引用其设计文档中的属性
- 标签格式：`# Feature: mcm-visualization-optimization, Property {number}: {property_text}`

**示例属性测试**：

```python
from hypothesis import given, strategies as st
import hypothesis.extra.numpy as npst

# Feature: mcm-visualization-optimization, Property 2: 配色方案约束
@given(
    n_colors=st.integers(min_value=5, max_value=6),
    plot_type=st.sampled_from(['heatmap', 'bar', 'radar'])
)
def test_color_palette_constraint(n_colors, plot_type):
    """
    Property: For any loaded color palette, the number of colors
    should be within 5-6 range, and all generated plots should
    only use these colors.
    """
    # Generate random color palette
    colors = {f"color_{i}": f"#{i:06x}" for i in range(n_colors)}
    config = StyleConfig(colors=colors, ...)
    
    style_manager = StyleManager(config)
    plot_generator = PlotGenerator(style_manager)
    
    # Generate random plot
    if plot_type == 'heatmap':
        data = np.random.rand(5, 5)
        fig = plot_generator.create_heatmap(data, ...)
    # ... other plot types
    
    # Extract colors used in the plot
    used_colors = extract_colors_from_figure(fig)
    
    # Assert all used colors are from the palette
    assert all(color in colors.values() for color in used_colors)
    assert len(colors) <= 6

# Feature: mcm-visualization-optimization, Property 23: 导出样式保真度
@given(
    data=npst.arrays(
        dtype=np.float64,
        shape=st.tuples(st.integers(3, 10), st.integers(3, 10))
    )
)
def test_export_style_preservation_roundtrip(data):
    """
    Property: For any plot, after exporting and reloading,
    all style elements (fonts, colors, transparency) should
    remain unchanged (round-trip property).
    """
    style_manager = StyleManager()
    plot_generator = PlotGenerator(style_manager)
    
    # Create original plot
    fig_original = plot_generator.create_heatmap(data, ...)
    original_style = extract_style_info(fig_original)
    
    # Export and reload
    exporter = FigureExporter()
    paths = exporter.export_figure(fig_original, "test_plot")
    fig_reloaded = load_figure_from_pdf(paths['pdf'])
    reloaded_style = extract_style_info(fig_reloaded)
    
    # Assert styles are preserved
    assert original_style['fonts'] == reloaded_style['fonts']
    assert original_style['colors'] == reloaded_style['colors']
    assert original_style['transparency'] == reloaded_style['transparency']

# Feature: mcm-visualization-optimization, Property 24: 迁移功能等价性
@given(
    data=npst.arrays(
        dtype=np.float64,
        shape=st.tuples(st.integers(10, 100),)
    )
)
def test_migration_functional_equivalence(data):
    """
    Property: For any migrated plotting script, using the same
    data before and after migration should produce the same
    data processing results (ignoring visual styling).
    """
    # Run original script
    original_result = run_original_script(data)
    
    # Migrate script
    migrator = PlotMigrator(style_manager, plot_generator)
    migrator.migrate_script("original_script.py", "migrated_script.py")
    
    # Run migrated script
    migrated_result = run_migrated_script(data)
    
    # Assert data processing results are equivalent
    np.testing.assert_array_almost_equal(
        original_result['processed_data'],
        migrated_result['processed_data']
    )
```

### 单元测试示例

```python
import pytest

def test_style_manager_loads_default_config():
    """Unit test: Verify default configuration loads successfully."""
    style_manager = StyleManager()
    config = style_manager.get_config()
    
    assert config is not None
    assert config.figure.dpi == 300
    assert len(config.colors) <= 6

def test_heatmap_with_empty_data_raises_error():
    """Unit test: Verify empty data raises appropriate error."""
    style_manager = StyleManager()
    plot_generator = PlotGenerator(style_manager)
    
    with pytest.raises(DataValidationError, match="empty"):
        plot_generator.create_heatmap(np.array([]), [], [])

def test_annotation_box_has_rounded_corners():
    """Unit test: Verify annotation boxes have rounded corners."""
    style_manager = StyleManager()
    annotation_system = AnnotationSystem(style_manager)
    
    fig, ax = plt.subplots()
    annotation_system.add_rounded_box(ax, "Test", (0.5, 0.5))
    
    # Check that the annotation has rounded corners
    annotations = ax.texts
    assert len(annotations) > 0
    # Verify bbox properties include rounded corners
    bbox = annotations[0].get_bbox_patch()
    assert bbox.get_boxstyle().startswith('round')

def test_export_creates_multiple_formats():
    """Unit test: Verify exporter creates all requested formats."""
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 2, 3])
    
    exporter = FigureExporter(output_dir="test_output")
    paths = exporter.export_figure(fig, "test_plot", formats=['png', 'pdf', 'svg'])
    
    assert 'png' in paths
    assert 'pdf' in paths
    assert 'svg' in paths
    assert all(path.exists() for path in paths.values())

def test_quality_validator_detects_low_dpi():
    """Unit test: Verify validator detects low DPI figures."""
    # Create low DPI figure
    fig = plt.figure(dpi=150)
    fig.savefig("low_dpi_test.png", dpi=150)
    
    validator = QualityValidator(StyleManager())
    result = validator.validate_figure(Path("low_dpi_test.png"))
    
    assert result['dpi']['passed'] == False
    assert result['dpi']['value'] < 300
```

### 集成测试

```python
def test_end_to_end_heatmap_generation():
    """Integration test: Full workflow from config to validated export."""
    # 1. Load configuration
    style_manager = StyleManager("config/style_config.yaml")
    
    # 2. Generate plot
    plot_generator = PlotGenerator(style_manager)
    data = np.random.rand(8, 8)
    fig = plot_generator.create_heatmap(
        data,
        row_labels=[f"Row {i}" for i in range(8)],
        col_labels=[f"Col {i}" for i in range(8)],
        title="Test Heatmap"
    )
    
    # 3. Export
    exporter = FigureExporter()
    paths = exporter.export_figure(fig, "integration_test_heatmap")
    
    # 4. Validate
    validator = QualityValidator(style_manager)
    result = validator.validate_figure(paths['png'])
    
    # 5. Assert quality
    assert result['overall_score'] >= 90
    assert result['dpi']['passed']
    assert result['colors']['passed']
    assert result['labels']['has_title']
    assert result['labels']['has_axes_labels']
```

### 测试覆盖率目标

- **代码覆盖率**：最低80%
- **属性覆盖率**：所有27个核心属性都有对应的属性测试
- **边界情况覆盖率**：每个公共API至少有一个边界情况测试
- **错误路径覆盖率**：所有自定义异常类型都有触发测试

### 持续集成

测试应在以下情况下自动运行：
- 每次代码提交
- Pull request创建时
- 每日定时构建

CI配置应包括：
- 运行所有单元测试和属性测试
- 生成覆盖率报告
- 运行质量验证器检查示例图表
- 失败时阻止合并

