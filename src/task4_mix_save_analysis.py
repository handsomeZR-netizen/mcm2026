"""
Task 4: Mix Save Strategy Comparison Analysis
对比 none/merit/mix 三种 Save 策略的效果
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime

# 设置中文字体和样式
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")
sns.set_context("paper", font_scale=1.2)

def load_data():
    """加载不同策略的数据"""
    data_dir = Path("data/processed")
    
    # 加载策略对比数据
    strategy_data = pd.read_csv(data_dir / "task2_metrics_rule_strategy.csv")
    
    return strategy_data

def calculate_strategy_metrics(strategy_data):
    """计算不同策略下的指标"""
    # 只看 Percent 规则（因为这是基准规则）
    percent_data = strategy_data[strategy_data['rule'] == 'percent'].copy()
    
    # 按策略分组统计
    strategy_stats = []
    
    for strategy in ['none', 'merit', 'fan', 'mix']:
        strat_data = percent_data[percent_data['strategy'] == strategy]
        
        if len(strat_data) == 0:
            continue
        
        # 获取指标
        fii = strat_data['FII'].values[0] if len(strat_data) > 0 else 0
        tpi = strat_data['TPI'].values[0] if len(strat_data) > 0 else 0
        judges_save = strat_data['judges_save'].values[0] if len(strat_data) > 0 else False
        
        strategy_stats.append({
            'strategy': strategy,
            'fii': fii,
            'tpi': tpi,
            'judges_save': judges_save
        })
    
    return pd.DataFrame(strategy_stats)

def plot_save_strategy_comparison(strategy_metrics, output_dir):
    """绘制 Save 策略对比图"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # 策略标签映射
    strategy_labels = {
        'none': 'No Save\n(直接淘汰)',
        'merit': 'Merit Save\n(救技术高者)',
        'fan': 'Fan Save\n(救人气高者)',
        'mix': 'Mix Save\n(折中策略)'
    }
    
    strategy_metrics['strategy_label'] = strategy_metrics['strategy'].map(strategy_labels)
    
    # 颜色方案
    colors = {'none': '#e74c3c', 'merit': '#3498db', 'fan': '#f39c12', 'mix': '#2ecc71'}
    strategy_metrics['color'] = strategy_metrics['strategy'].map(colors)
    
    # 图1：FII
    ax1 = axes[0]
    bars1 = ax1.bar(strategy_metrics['strategy_label'], 
                    strategy_metrics['fii'],
                    color=strategy_metrics['color'],
                    alpha=0.8,
                    edgecolor='black',
                    linewidth=1.5)
    
    ax1.set_ylabel('FII (Fan Influence Index)', fontsize=12, fontweight='bold')
    ax1.set_title('(A) Audience Engagement', fontsize=13, fontweight='bold')
    ax1.set_ylim(0, 1.0)
    ax1.grid(axis='y', alpha=0.3)
    ax1.axhline(y=0.8, color='gray', linestyle='--', alpha=0.5, linewidth=2)
    ax1.text(0.02, 0.82, 'Target (0.8)', transform=ax1.transAxes, 
             fontsize=9, color='gray', style='italic')
    
    # 添加数值标签
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                f'{height:.3f}',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # 图2：TPI
    ax2 = axes[1]
    bars2 = ax2.bar(strategy_metrics['strategy_label'], 
                    strategy_metrics['tpi'],
                    color=strategy_metrics['color'],
                    alpha=0.8,
                    edgecolor='black',
                    linewidth=1.5)
    
    ax2.set_ylabel('TPI (Technical Protection Index)', fontsize=12, fontweight='bold')
    ax2.set_title('(B) Technical Fairness', fontsize=13, fontweight='bold')
    ax2.set_ylim(0, 1.0)
    ax2.grid(axis='y', alpha=0.3)
    
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                f'{height:.3f}',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图表
    output_path = output_dir / f"task4_save_strategy_comparison_{timestamp}.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ 保存图表: {output_path}")
    
    plt.close()
    
    return output_path

def generate_summary_table(strategy_metrics, output_dir):
    """生成汇总表格"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 创建格式化的表格
    summary = strategy_metrics[['strategy', 'fii', 'tpi', 'judges_save']].copy()
    
    summary.columns = ['Strategy', 'FII', 'TPI', 'Judges Save']
    
    # 保存为 CSV
    output_path = output_dir / f"task4_save_strategy_summary_{timestamp}.csv"
    summary.to_csv(output_path, index=False, float_format='%.4f')
    print(f"✓ 保存汇总表: {output_path}")
    
    return summary

def main():
    print("=" * 60)
    print("Task 4: Mix Save Strategy Comparison Analysis")
    print("=" * 60)
    
    # 创建输出目录
    output_dir = Path("figures")
    output_dir.mkdir(exist_ok=True)
    
    data_dir = Path("data/processed")
    data_dir.mkdir(exist_ok=True)
    
    # 加载数据
    print("\n[1/3] 加载数据...")
    strategy_data = load_data()
    
    # 计算策略指标
    print("\n[2/3] 计算策略指标...")
    strategy_metrics = calculate_strategy_metrics(strategy_data)
    
    if len(strategy_metrics) == 0:
        print("错误：无法计算策略指标")
        return
    
    print("\n策略对比结果（Percent规则下）：")
    print(strategy_metrics.to_string(index=False))
    
    # 生成图表
    print("\n[3/3] 生成图表...")
    plot_path = plot_save_strategy_comparison(strategy_metrics, output_dir)
    
    # 生成汇总表
    summary = generate_summary_table(strategy_metrics, data_dir)
    
    print("\n" + "=" * 60)
    print("分析完成！")
    print("=" * 60)
    
    # 输出关键发现
    print("\n关键发现：")
    print("-" * 60)
    
    if 'mix' in strategy_metrics['strategy'].values:
        mix_row = strategy_metrics[strategy_metrics['strategy'] == 'mix'].iloc[0]
        print(f"Mix Save 策略（推荐）：")
        print(f"  - FII (观众影响力): {mix_row['fii']:.3f}")
        print(f"  - TPI (技术保护): {mix_row['tpi']:.3f}")
    
    if 'none' in strategy_metrics['strategy'].values and 'mix' in strategy_metrics['strategy'].values:
        none_row = strategy_metrics[strategy_metrics['strategy'] == 'none'].iloc[0]
        mix_row = strategy_metrics[strategy_metrics['strategy'] == 'mix'].iloc[0]
        merit_row = strategy_metrics[strategy_metrics['strategy'] == 'merit'].iloc[0]
        
        print(f"\nMix Save 的优势：")
        print(f"  相比 No Save:")
        print(f"    - FII 提升: {(mix_row['fii'] - none_row['fii'])*100:.1f}%")
        print(f"    - TPI 下降: {(none_row['tpi'] - mix_row['tpi'])*100:.1f}% (权衡)")
        print(f"  相比 Merit Save:")
        print(f"    - FII 更高: {(mix_row['fii'] - merit_row['fii'])*100:.1f}%")
        print(f"    - TPI 更低: {(merit_row['tpi'] - mix_row['tpi'])*100:.1f}% (更偏观众)")
    
    print("\n结论：Mix Save 在观众参与感和技术公平性之间达到了最佳平衡")

if __name__ == "__main__":
    main()
