# 需求文档：美赛论文可视化优化系统

## 简介

本系统旨在为美赛（MCM）数学建模竞赛论文《基于贝叶斯反演的《与星共舞》观众投票重建》创建统一的"论文级"可视化系统。目标是将所有图表质量提升到O奖（Outstanding Winner）标准，通过统一的样式系统、高级视觉元素和专业排版实现视觉一致性和学术专业性。

## 术语表

- **Visualization_System**: 可视化系统，负责生成和管理所有论文图表
- **Style_Manager**: 样式管理器，管理全局绘图样式和配置
- **Plot_Generator**: 图表生成器，根据数据和样式配置生成具体图表
- **Figure_Exporter**: 图表导出器，将图表导出为高质量矢量格式
- **Color_Palette**: 配色方案，定义论文中使用的统一颜色集合
- **Annotation_System**: 注释系统，管理图表中的文字标注和说明框
- **O_Award_Standard**: O奖标准，指美赛Outstanding Winner级别的图表质量要求

## 需求

### 需求 1：统一样式系统

**用户故事**：作为论文作者，我希望建立统一的绘图样式系统，以确保所有图表具有一致的专业外观。

#### 验收标准

1. THE Style_Manager SHALL load SciencePlots library and configure global rcParams for all matplotlib plots
2. THE Style_Manager SHALL define a unified Color_Palette with maximum 5-6 colors suitable for academic publications
3. THE Style_Manager SHALL configure font families (serif for body text, sans-serif for annotations) with consistent sizes
4. THE Style_Manager SHALL set default figure DPI to minimum 300 for high-quality output
5. THE Style_Manager SHALL configure line widths, marker sizes, and grid styles consistently across all plot types
6. WHEN any Plot_Generator creates a figure, THE Visualization_System SHALL automatically apply the unified style configuration

### 需求 2：高级流程图和框架图

**用户故事**：作为论文作者，我希望创建专业的流程图和框架图，以清晰展示系统架构和算法流程。

#### 验收标准

1. THE Plot_Generator SHALL create flowcharts with grouped elements using dashed boundary boxes
2. THE Plot_Generator SHALL apply unified Color_Palette to flowchart elements with semantic color coding
3. THE Plot_Generator SHALL use rounded rectangles for process nodes and diamonds for decision nodes
4. THE Plot_Generator SHALL add directional arrows with clear labels between connected nodes
5. WHEN rendering complex workflows, THE Plot_Generator SHALL organize elements hierarchically with proper spacing
6. THE Figure_Exporter SHALL export flowcharts as vector graphics (SVG or PDF) for scalability

### 需求 3：信息图风格的柱状图

**用户故事**：作为论文作者，我希望创建具有渐变色和专业注释的柱状图，以提升数据展示的视觉吸引力。

#### 验收标准

1. THE Plot_Generator SHALL create bar charts with gradient color fills from Color_Palette
2. THE Plot_Generator SHALL use rounded corners for bar chart rectangles
3. THE Annotation_System SHALL add rounded annotation boxes with semi-transparent backgrounds
4. THE Annotation_System SHALL position annotations to avoid overlapping with data elements
5. WHEN displaying multiple categories, THE Plot_Generator SHALL use subtle color variations within the unified palette
6. THE Plot_Generator SHALL minimize or remove chart borders (spines) for a clean appearance

### 需求 4：背景水印和主题化排版

**用户故事**：作为论文作者，我希望为图表添加品牌化元素，以增强论文的专业性和识别度。

#### 验收标准

1. THE Plot_Generator SHALL add semi-transparent watermarks to figures with configurable text and position
2. THE Plot_Generator SHALL support custom background patterns or subtle textures
3. THE Style_Manager SHALL define consistent margin and padding rules for all figure types
4. WHEN adding watermarks, THE Plot_Generator SHALL ensure they do not obscure critical data
5. THE Plot_Generator SHALL support optional themed borders or frames for figures

### 需求 5：优化的热力图

**用户故事**：作为论文作者，我希望创建干净、易读的热力图，以有效展示矩阵数据和相关性。

#### 验收标准

1. THE Plot_Generator SHALL create heatmaps with appropriate whitespace between cells
2. THE Plot_Generator SHALL use perceptually uniform colormaps (e.g., viridis, plasma) from Color_Palette
3. THE Plot_Generator SHALL position colorbars with proper size ratio (not too wide) and clear labels
4. THE Plot_Generator SHALL add cell value annotations when matrix size is small enough (e.g., < 10x10)
5. WHEN displaying correlation matrices, THE Plot_Generator SHALL use diverging colormaps centered at zero
6. THE Plot_Generator SHALL remove unnecessary gridlines and minimize visual clutter

### 需求 6：雷达图优化

**用户故事**：作为论文作者，我希望创建清晰的雷达图，以展示多维度评估结果。

#### 验收标准

1. THE Plot_Generator SHALL create radar charts with evenly spaced axes and clear labels
2. THE Plot_Generator SHALL use semi-transparent fills with colors from Color_Palette
3. THE Plot_Generator SHALL add gridlines at regular intervals for value reference
4. WHEN comparing multiple entities, THE Plot_Generator SHALL use distinct line styles and colors
5. THE Plot_Generator SHALL ensure axis labels are readable and do not overlap
6. THE Plot_Generator SHALL normalize data ranges appropriately for fair comparison

### 需求 7：生存曲线和时间序列图

**用户故事**：作为论文作者，我希望创建专业的生存曲线和时间序列图，以展示动态变化过程。

#### 验收标准

1. THE Plot_Generator SHALL create survival curves with confidence intervals shown as shaded regions
2. THE Plot_Generator SHALL use distinct line styles (solid, dashed, dotted) for multiple curves
3. THE Plot_Generator SHALL add risk tables below survival curves when appropriate
4. WHEN plotting time series, THE Plot_Generator SHALL use appropriate date formatters for x-axis
5. THE Plot_Generator SHALL highlight significant events or transitions with vertical lines and annotations
6. THE Annotation_System SHALL add legends outside the plot area to avoid obscuring data

### 需求 8：矢量图导出系统

**用户故事**：作为论文作者，我希望将所有图表导出为高质量矢量格式，以确保在论文中的清晰度。

#### 验收标准

1. THE Figure_Exporter SHALL export figures in both PNG (300+ DPI) and vector formats (PDF/SVG)
2. THE Figure_Exporter SHALL preserve all styling elements (fonts, colors, transparency) during export
3. THE Figure_Exporter SHALL use tight bounding boxes to minimize whitespace in exported files
4. THE Figure_Exporter SHALL embed fonts in PDF exports for consistent rendering
5. WHEN exporting multiple figures, THE Figure_Exporter SHALL maintain consistent dimensions and aspect ratios
6. THE Figure_Exporter SHALL validate that exported files are not corrupted and can be opened

### 需求 9：注释和标签系统

**用户故事**：作为论文作者，我希望使用专业的注释系统，以清晰标注图表中的关键信息。

#### 验收标准

1. THE Annotation_System SHALL create rounded annotation boxes with configurable background colors and transparency
2. THE Annotation_System SHALL support arrow annotations pointing to specific data points
3. THE Annotation_System SHALL automatically adjust annotation positions to avoid overlaps
4. THE Annotation_System SHALL use consistent font sizes and styles from Style_Manager
5. WHEN adding multiple annotations, THE Annotation_System SHALL maintain visual hierarchy
6. THE Annotation_System SHALL prefer direct labeling over legends when space permits

### 需求 10：现有图表迁移

**用户故事**：作为论文作者，我希望将现有的所有图表脚本迁移到新的样式系统，以实现统一的视觉效果。

#### 验收标准

1. THE Visualization_System SHALL identify all existing plotting scripts in the src/ directory
2. THE Visualization_System SHALL refactor existing plots to use the unified Style_Manager
3. THE Visualization_System SHALL preserve all data processing logic while updating visual styling
4. WHEN migrating plots, THE Visualization_System SHALL maintain backward compatibility with existing data files
5. THE Visualization_System SHALL generate comparison reports showing before/after visual improvements
6. THE Visualization_System SHALL update all figure references in the paper markdown file

### 需求 11：配置管理系统

**用户故事**：作为论文作者，我希望通过配置文件管理样式参数，以便快速调整整体视觉风格。

#### 验收标准

1. THE Style_Manager SHALL load style configurations from a centralized YAML or JSON file
2. THE Style_Manager SHALL support configuration inheritance and overrides for specific plot types
3. THE Style_Manager SHALL validate configuration parameters against allowed value ranges
4. WHEN configuration is updated, THE Visualization_System SHALL reload styles without code changes
5. THE Style_Manager SHALL provide default configurations that meet O_Award_Standard
6. THE Style_Manager SHALL log warnings when configurations deviate from best practices

### 需求 12：质量验证系统

**用户故事**：作为论文作者，我希望自动验证所有图表是否符合O奖标准，以确保质量一致性。

#### 验收标准

1. THE Visualization_System SHALL check that all exported figures meet minimum DPI requirements (300+)
2. THE Visualization_System SHALL verify that all figures use colors from the approved Color_Palette
3. THE Visualization_System SHALL validate that font sizes are within readable ranges (8-12pt for body, 10-14pt for titles)
4. THE Visualization_System SHALL check that all figures have proper axis labels and titles
5. WHEN validation fails, THE Visualization_System SHALL generate a detailed report with specific issues
6. THE Visualization_System SHALL provide a summary score indicating overall compliance with O_Award_Standard
