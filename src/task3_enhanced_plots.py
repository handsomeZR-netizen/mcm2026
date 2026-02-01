"""
Task 3 Enhanced Plots - O-Prize Quality Visualization
按照评委反馈的美学标准重绘所有图表
"""

import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Rectangle

# 设置全局样式
sns.set_theme(style='whitegrid', context='paper')
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['figure.dpi'] = 300

# 定义配色方案
COLORS = {
    'judges': '#1f77b4',  # Navy blue (理性/技术)
    'fans': '#ff7f0e',    # Orange (感性/人气)
    'protect': '#2ca02c', # Green (保护因子)
    'risk': '#d62728',    # Red (风险因子)
    'neutral': '#7f7f7f', # Gray (中性)
    'line': '#cccccc',    # Light gray (连线)
}


def plot_dumbbell_chart(coef_df, output_path):
    """
    绘制哑铃图 - 评委vs观众系数对比
    按照差异大小排序，突出关键发现
    """
    # 准备数据
    df = coef_df.copy()
    df['gap'] = abs(df['judge_coef'] - df['fan_coef'])
    df = df.sort_values('gap', ascending=True)  # 差异大的在上面
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(8, 6))
    
    y_pos = np.arange(len(df))
    
    # 绘制连线
    for i, (_, row) in enumerate(df.iterrows()):
        ax.plot(
            [row['judge_coef'], row['fan_coef']],
            [i, i],
            color=COLORS['line'],
            linewidth=0.8,
            zorder=1
        )
    
    # 绘制点
    ax.scatter(df['judge_coef'], y_pos, 
              color=COLORS['judges'], s=80, label='Judges Model',
              zorder=2, edgecolor='white', linewidth=0.5)
    ax.scatter(df['fan_coef'], y_pos,
              color=COLORS['fans'], s=80, label='Fans Model',
              zorder=2, edgecolor='white', linewidth=0.5)
    
    # 标注最大差异
    max_gap_idx = df['gap'].idxmax()
    max_gap_row = df.loc[max_gap_idx]
    max_gap_y = df.index.get_loc(max_gap_idx)
    
    ax.annotate(
        'Largest divergence',
        xy=((max_gap_row['judge_coef'] + max_gap_row['fan_coef']) / 2, max_gap_y),
        xytext=(10, 10),
        textcoords='offset points',
        fontsize=8,
        color='red',
        arrowprops=dict(arrowstyle='->', color='red', lw=0.8)
    )
    
    # 设置标签
    ax.set_yticks(y_pos)
    ax.set_yticklabels(df['term'])
    ax.set_xlabel('Coefficient (Standardized)')
    ax.set_title('Judges vs Fans: Coefficient Comparison')
    ax.axvline(0, color='black', linewidth=0.8, linestyle='--', alpha=0.3)
    ax.legend(loc='lower right')
    ax.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Dumbbell chart saved: {output_path}")


def plot_cox_forest(cox_df, output_path):
    """
    绘制Cox森林图 - 风险比可视化
    使用对数刻度，颜色编码保护/风险因子
    """
    # 准备数据
    df = cox_df.copy()
    df = df.sort_values('hazard_ratio')  # 保护因子在上
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(8, 6))
    
    y_pos = np.arange(len(df))
    
    # 颜色编码
    colors = [COLORS['protect'] if hr < 1 else COLORS['risk'] 
              for hr in df['hazard_ratio']]
    
    # 绘制置信区间
    for i, (_, row) in enumerate(df.iterrows()):
        ax.plot(
            [row['ci_low'], row['ci_high']],
            [i, i],
            color=colors[i],
            linewidth=2,
            alpha=0.6,
            zorder=1
        )
    
    # 绘制点（大小反映显著性）
    sizes = [100 if p < 0.001 else 80 if p < 0.01 else 60 if p < 0.05 else 40
             for p in df['p']]
    
    ax.scatter(df['hazard_ratio'], y_pos,
              color=colors, s=sizes, zorder=2,
              edgecolor='white', linewidth=0.8)
    
    # 参考线
    ax.axvline(1, color='black', linewidth=1.5, linestyle='--', 
              label='No Effect (HR=1)', zorder=0)
    
    # 设置对数刻度
    ax.set_xscale('log')
    ax.set_xlim(0.1, 10)
    
    # 设置标签
    ax.set_yticks(y_pos)
    ax.set_yticklabels(df['term'])
    ax.set_xlabel('Hazard Ratio (Log Scale)')
    ax.set_title('Cox Proportional Hazards Model: Elimination Risk Factors')
    
    # 添加图例
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Protective (HR<1)',
               markerfacecolor=COLORS['protect'], markersize=8),
        Line2D([0], [0], marker='o', color='w', label='Risk (HR>1)',
               markerfacecolor=COLORS['risk'], markersize=8),
        Line2D([0], [0], color='black', linewidth=1.5, linestyle='--',
               label='No Effect (HR=1)')
    ]
    ax.legend(handles=legend_elements, loc='lower right')
    
    ax.grid(axis='x', alpha=0.3, which='both')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Cox forest plot saved: {output_path}")


def plot_pro_buff_caterpillar(pro_buff_df, output_path):
    """
    绘制Pro Buff毛毛虫图
    S型曲线，高亮Top/Bottom，背景带表示显著性
    """
    # 准备数据
    df = pro_buff_df.copy()
    df = df.sort_values('buff')
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x_pos = np.arange(len(df))
    
    # 背景带（±1 SD）
    mean_buff = df['buff'].mean()
    std_buff = df['buff'].std()
    ax.axhspan(mean_buff - std_buff, mean_buff + std_buff,
              color='lightgray', alpha=0.3, label='±1 SD')
    
    # 绘制置信区间
    for i, (_, row) in enumerate(df.iterrows()):
        ax.plot(
            [i, i],
            [row['ci_low'], row['ci_high']],
            color=COLORS['neutral'],
            linewidth=1,
            alpha=0.5,
            zorder=1
        )
    
    # 绘制S型曲线
    ax.plot(x_pos, df['buff'], color=COLORS['neutral'], 
           linewidth=1, alpha=0.5, zorder=1)
    
    # 绘制点（中间的小，Top/Bottom的大）
    colors = []
    sizes = []
    for i, buff in enumerate(df['buff']):
        if i < 3:  # Bottom 3
            colors.append(COLORS['risk'])
            sizes.append(100)
        elif i >= len(df) - 3:  # Top 3
            colors.append(COLORS['protect'])
            sizes.append(100)
        else:
            colors.append(COLORS['neutral'])
            sizes.append(30)
    
    ax.scatter(x_pos, df['buff'], color=colors, s=sizes,
              zorder=2, edgecolor='white', linewidth=0.8)
    
    # 标注Top 3和Bottom 3
    for i in range(3):
        # Bottom 3
        ax.text(i, df.iloc[i]['buff'] - 0.02, df.iloc[i]['pro'],
               ha='center', va='top', fontsize=7, color=COLORS['risk'])
        # Top 3
        idx = len(df) - 3 + i
        ax.text(idx, df.iloc[idx]['buff'] + 0.02, df.iloc[idx]['pro'],
               ha='center', va='bottom', fontsize=7, color=COLORS['protect'])
    
    # 参考线
    ax.axhline(0, color='black', linewidth=0.8, linestyle='--', alpha=0.5)
    
    # 设置标签
    ax.set_xlabel('Professional Dancers (Ranked by Buff)')
    ax.set_ylabel('Pro Buff (Standardized)')
    ax.set_title('Professional Dancer Effect: Caterpillar Plot')
    ax.set_xticks([])  # 隐藏x轴刻度（太多了）
    
    ax.legend(loc='upper left')
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Pro Buff caterpillar plot saved: {output_path}")


def plot_sensitivity_heatmap(sensitivity_df, output_path):
    """
    绘制敏感性分析热力图
    RdBu色阶，数值标注
    """
    # 准备数据
    df = sensitivity_df.set_index('variant')
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(8, 5))
    
    # 绘制热力图
    sns.heatmap(
        df,
        cmap='RdBu_r',  # 红色=高一致性，蓝色=低一致性
        vmin=0,
        vmax=1,
        annot=True,
        fmt='.2f',
        linewidths=0.5,
        linecolor='white',
        cbar_kws={'label': 'Consistency Score'},
        ax=ax
    )
    
    ax.set_title('Sensitivity Analysis: Model Robustness Check')
    ax.set_xlabel('Consistency Metric')
    ax.set_ylabel('Model Variant')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Sensitivity heatmap saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Task3 Enhanced Plots')
    parser.add_argument('--coef', default='data/processed/task3_model_coefficients.csv')
    parser.add_argument('--cox', default='data/processed/task3_cox_summary.csv')
    parser.add_argument('--pro-buff', default='data/processed/task3_pro_buff.csv')
    parser.add_argument('--sensitivity', default='data/processed/task3_sensitivity_summary.csv')
    parser.add_argument('--output-dir', default='figures')
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    run_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print("🎨 Task 3 Enhanced Plots - O-Prize Quality")
    print("=" * 60)
    
    # 1. Dumbbell Chart
    if Path(args.coef).exists():
        coef_df = pd.read_csv(args.coef)
        plot_dumbbell_chart(
            coef_df,
            output_dir / f'task3_coef_dumbbell_enhanced_{run_ts}.png'
        )
    
    # 2. Cox Forest Plot
    if Path(args.cox).exists():
        cox_df = pd.read_csv(args.cox)
        plot_cox_forest(
            cox_df,
            output_dir / f'task3_cox_forest_enhanced_{run_ts}.png'
        )
    
    # 3. Pro Buff Caterpillar
    if Path(args.pro_buff).exists():
        pro_buff_df = pd.read_csv(args.pro_buff)
        plot_pro_buff_caterpillar(
            pro_buff_df,
            output_dir / f'task3_pro_buff_caterpillar_enhanced_{run_ts}.png'
        )
    
    # 4. Sensitivity Heatmap
    if Path(args.sensitivity).exists():
        sensitivity_df = pd.read_csv(args.sensitivity)
        plot_sensitivity_heatmap(
            sensitivity_df,
            output_dir / f'task3_sensitivity_heatmap_enhanced_{run_ts}.png'
        )
    
    print("=" * 60)
    print("✅ All enhanced plots generated successfully!")
    print(f"📁 Output directory: {output_dir}")


if __name__ == '__main__':
    main()
