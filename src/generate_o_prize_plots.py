"""
简化版O奖图表生成脚本
只生成最核心的两个图表：Pareto Frontier 和 Weight Curve
"""
import sys
from pathlib import Path

# 最小化导入，避免NumPy兼容性问题
try:
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装: pandas, matplotlib, numpy")
    sys.exit(1)

def plot_pareto_frontier(metrics_path, output_path):
    """生成Pareto Frontier图表"""
    print("正在生成 Pareto Frontier...")
    
    # 读取数据
    df = pd.read_csv(metrics_path)
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # 规则样式
    styles = {
        'rank': {'color': '#E74C3C', 'marker': 's', 'size': 200, 'label': 'Rank Rule'},
        'percent': {'color': '#3498DB', 'marker': 'o', 'size': 200, 'label': 'Percent Rule'},
        'adaptive_percent': {'color': '#2ECC71', 'marker': '*', 'size': 400, 'label': 'Adaptive Percent (Ours)'},
        'official': {'color': '#E67E22', 'marker': 'd', 'size': 200, 'label': 'Official Rule'}
    }
    
    # 绘制每个规则
    for rule, style in styles.items():
        data = df[df['rule'] == rule]
        if len(data) > 0:
            ax.scatter(
                data['FII'], data['TPI'],
                c=style['color'], marker=style['marker'], s=style['size'],
                label=style['label'], edgecolors='black', linewidths=1.5,
                alpha=0.9, zorder=10
            )
            
            # 添加标签
            for _, row in data.iterrows():
                ax.annotate(
                    style['label'].split()[0],
                    (row['FII'], row['TPI']),
                    xytext=(10, 10), textcoords='offset points',
                    fontsize=10, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor=style['color'], alpha=0.3)
                )
    
    # 标注理想区域
    ax.text(0.85, 0.80, 'Ideal Zone\n(High FII, High TPI)', 
            ha='center', va='center', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))
    
    ax.text(0.65, 0.58, 'Low Engagement', 
            ha='center', va='center', fontsize=9, style='italic',
            bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.2))
    
    ax.text(0.82, 0.58, 'Low Fairness', 
            ha='center', va='center', fontsize=9, style='italic',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.3))
    
    # 设置
    ax.set_xlabel('FII (Fan Influence Index)\n← Lower | Higher →', 
                  fontsize=12, fontweight='bold')
    ax.set_ylabel('TPI (Technical Protection Index)\n← Lower | Higher →', 
                  fontsize=12, fontweight='bold')
    ax.set_title('Pareto Frontier: FII vs TPI Tradeoff\nAdaptive Percent Achieves Better Balance',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='lower left', fontsize=10, framealpha=0.9)
    ax.grid(True, alpha=0.2)
    ax.set_xlim(0.62, 0.87)
    ax.set_ylim(0.55, 0.82)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ 已保存: {output_path}")


def plot_weight_curve(output_path, w_min=0.45, w_max=0.55):
    """生成Weight Curve图表"""
    print("正在生成 Weight Curve...")
    
    # 生成数据
    weeks = np.arange(1, 11)
    total_weeks = 10
    judge_weights = [w_min + (w_max - w_min) * (w - 1) / (total_weeks - 1) for w in weeks]
    fan_weights = [1 - jw for jw in judge_weights]
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 绘制曲线
    ax.plot(weeks, judge_weights, 'o-', color='#E74C3C', linewidth=3, 
            markersize=10, label='Judge Weight', markeredgecolor='black', markeredgewidth=1.5)
    ax.plot(weeks, fan_weights, 's-', color='#3498DB', linewidth=3, 
            markersize=10, label='Fan Weight', markeredgecolor='black', markeredgewidth=1.5)
    
    # 50%参考线
    ax.axhline(y=0.5, color='gray', linestyle='--', linewidth=2, alpha=0.5, label='Equal (50%)')
    
    # 阴影区域
    ax.fill_between(weeks, 0, judge_weights, alpha=0.2, color='#E74C3C')
    ax.fill_between(weeks, judge_weights, 1, alpha=0.2, color='#3498DB')
    
    # 标注
    ax.annotate(
        'Early Stage:\nFans dominate\n(55% influence)',
        xy=(2, fan_weights[1]),
        xytext=(3, 0.7),
        fontsize=11,
        fontweight='bold',
        arrowprops=dict(arrowstyle='->', lw=2, color='#3498DB'),
        bbox=dict(boxstyle='round', facecolor='#3498DB', alpha=0.3)
    )
    
    ax.annotate(
        'Late Stage:\nJudges dominate\n(55% influence)',
        xy=(9, judge_weights[8]),
        xytext=(7, 0.7),
        fontsize=11,
        fontweight='bold',
        arrowprops=dict(arrowstyle='->', lw=2, color='#E74C3C'),
        bbox=dict(boxstyle='round', facecolor='#E74C3C', alpha=0.3)
    )
    
    # 设置
    ax.set_xlabel('Week Number', fontsize=13, fontweight='bold')
    ax.set_ylabel('Weight (Influence)', fontsize=13, fontweight='bold')
    ax.set_title(f'Adaptive Weight Curve: Dynamic Balance Over Time\n(w_min={w_min}, w_max={w_max})',
                 fontsize=14, fontweight='bold')
    ax.set_ylim(0, 1)
    ax.set_xlim(0.5, 10.5)
    ax.set_xticks(weeks)
    ax.set_yticks(np.arange(0, 1.1, 0.1))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
    ax.legend(loc='center right', fontsize=11, framealpha=0.9)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ 已保存: {output_path}")


def main():
    from datetime import datetime
    
    print("\n" + "="*70)
    print("O奖核心图表生成")
    print("="*70 + "\n")
    
    # 设置路径
    metrics_path = Path('data/processed/task2_metrics_rule_default.csv')
    output_dir = Path('figures')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 检查数据文件
    if not metrics_path.exists():
        print(f"错误: 找不到数据文件 {metrics_path}")
        print("请确保已运行 Task 2 的模拟脚本")
        return
    
    # 生成图表
    try:
        # 1. Pareto Frontier
        pareto_path = output_dir / f'task4_pareto_frontier_{timestamp}.png'
        plot_pareto_frontier(metrics_path, pareto_path)
        
        # 2. Weight Curve
        weight_path = output_dir / f'task4_weight_curve_{timestamp}.png'
        plot_weight_curve(weight_path)
        
        print("\n" + "="*70)
        print("完成！生成的图表：")
        print("="*70)
        print(f"1. Pareto Frontier: {pareto_path.name}")
        print(f"2. Weight Curve: {weight_path.name}")
        print("\n这两个图表是O奖论文的核心可视化！")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
