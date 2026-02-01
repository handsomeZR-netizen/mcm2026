"""
分析：如果在四位争议明星的赛季增加 Judges' Save 机制，他们被淘汰的可能性

四位明星：
1. Jerry Rice (S2)
2. Billy Ray Cyrus (S4)
3. Bristol Palin (S11)
4. Bobby Bones (S27)

分析思路：
- 读取后验投票数据
- 对每位明星的每周，计算：
  1. 原规则下的淘汰概率
  2. 加入 Judges' Save 后的淘汰概率（需要进入 Bottom 2 且被评委淘汰）
- 对比差异
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# 设置绘图风格
sns.set_theme(style="whitegrid")
sns.set_context("talk", font_scale=0.9)
plt.rcParams.update({
    "figure.facecolor": "#FFFFFF",
    "axes.facecolor": "#F7F8FA",
    "grid.color": "#DADDE2",
    "axes.edgecolor": "#2B2D42",
    "axes.labelcolor": "#2B2D42",
    "xtick.color": "#2B2D42",
    "ytick.color": "#2B2D42",
    "font.family": "DejaVu Sans",
})

palette_map = {
    "original": "#E63946",      # 红色 - 原规则
    "with_save": "#2A9D8F",     # 绿色 - 加入Save
    "difference": "#F4A261",    # 橙色 - 差异
    "muted": "#8D99AE",
}

# 四位争议明星
CELEBRITIES = {
    'Jerry Rice': {'season': 2, 'name': 'Jerry Rice'},
    'Billy Ray Cyrus': {'season': 4, 'name': 'Billy Ray Cyrus'},
    'Bristol Palin': {'season': 11, 'name': 'Bristol Palin'},
    'Bobby Bones': {'season': 27, 'name': 'Bobby Bones'},
}


def load_data():
    """加载数据"""
    # 后验投票数据
    posterior = pd.read_csv('data/processed/abc_weekly_posterior.csv')
    
    # 周级真实数据
    weekly = pd.read_csv('data/processed/dwts_weekly_long.csv')
    
    return posterior, weekly


def calculate_elimination_prob_original(df_week, celebrity_name, rule='percent'):
    """
    计算原规则下的淘汰概率
    
    假设：使用后验均值作为投票份额，计算该选手的综合得分排名
    如果排名最低，则被淘汰
    """
    # 获取该选手的数据
    celeb_data = df_week[df_week['celebrity_name'] == celebrity_name].iloc[0]
    
    # 计算综合得分
    if rule == 'rank':
        # Rank规则：排名相加（越小越好）
        judge_rank = df_week['judge_total'].rank(ascending=False)
        fan_rank = df_week['posterior_mean'].rank(ascending=False)
        combined = judge_rank + fan_rank
        # 排名最大者被淘汰
        is_eliminated = combined[df_week['celebrity_name'] == celebrity_name].iloc[0] == combined.max()
    else:
        # Percent规则：百分比相加（越大越好）
        judge_pct = df_week['judge_total'] / df_week['judge_total'].sum()
        fan_pct = df_week['posterior_mean']
        combined = 0.5 * judge_pct + 0.5 * fan_pct
        # 得分最低者被淘汰
        is_eliminated = combined[df_week['celebrity_name'] == celebrity_name].iloc[0] == combined.min()
    
    return 1.0 if is_eliminated else 0.0


def calculate_elimination_prob_with_save(df_week, celebrity_name, rule='percent'):
    """
    计算加入 Judges' Save 后的淘汰概率
    
    逻辑：
    1. 先确定 Bottom 2
    2. 如果该选手在 Bottom 2 中，假设评委会根据评委分数决定救谁
       - 评委分高的被救，评委分低的被淘汰
    3. 如果不在 Bottom 2，淘汰概率为 0
    """
    # 计算综合得分
    if rule == 'rank':
        judge_rank = df_week['judge_total'].rank(ascending=False)
        fan_rank = df_week['posterior_mean'].rank(ascending=False)
        combined = judge_rank + fan_rank
        # Bottom 2: 排名最大的两个
        bottom_2_idx = combined.nlargest(2).index
    else:
        judge_pct = df_week['judge_total'] / df_week['judge_total'].sum()
        fan_pct = df_week['posterior_mean']
        combined = 0.5 * judge_pct + 0.5 * fan_pct
        # Bottom 2: 得分最小的两个
        bottom_2_idx = combined.nsmallest(2).index
    
    # 检查该选手是否在 Bottom 2
    celeb_idx = df_week[df_week['celebrity_name'] == celebrity_name].index[0]
    
    if celeb_idx not in bottom_2_idx:
        return 0.0  # 不在 Bottom 2，不会被淘汰
    
    # 在 Bottom 2 中，评委会救评委分高的
    bottom_2_data = df_week.loc[bottom_2_idx]
    judge_scores = bottom_2_data['judge_total']
    
    # 评委分低的被淘汰
    eliminated_idx = judge_scores.idxmin()
    
    return 1.0 if eliminated_idx == celeb_idx else 0.0


def analyze_celebrity(celebrity_name, season, posterior, weekly):
    """分析单个明星"""
    print(f"\n分析 {celebrity_name} (Season {season})...")
    
    # 筛选该赛季该明星的数据
    celeb_posterior = posterior[
        (posterior['season'] == season) & 
        (posterior['celebrity_name'] == celebrity_name)
    ].copy()
    
    celeb_weekly = weekly[
        (weekly['season'] == season) & 
        (weekly['celebrity_name'] == celebrity_name)
    ].copy()
    
    # 确定规则
    if season <= 2:
        rule = 'rank'
    else:
        rule = 'percent'
    
    results = []
    
    for week in sorted(celeb_posterior['week'].unique()):
        # 获取该周所有选手的数据
        week_posterior = posterior[
            (posterior['season'] == season) & 
            (posterior['week'] == week)
        ].copy()
        
        week_weekly = weekly[
            (weekly['season'] == season) & 
            (weekly['week'] == week)
        ].copy()
        
        # 合并数据
        df_week = week_weekly.merge(
            week_posterior[['celebrity_name', 'posterior_mean', 'posterior_sd']],
            on='celebrity_name',
            how='left'
        )
        
        # 跳过没有后验数据的周
        if df_week['posterior_mean'].isna().any():
            continue
        
        # 跳过已经被淘汰的周（judge_total为0或NaN）
        if df_week[df_week['celebrity_name'] == celebrity_name]['judge_total'].iloc[0] == 0:
            continue
        
        # 计算两种情况下的淘汰概率
        prob_original = calculate_elimination_prob_original(df_week, celebrity_name, rule)
        prob_with_save = calculate_elimination_prob_with_save(df_week, celebrity_name, rule)
        
        results.append({
            'celebrity_name': celebrity_name,
            'season': season,
            'week': week,
            'rule': rule,
            'prob_original': prob_original,
            'prob_with_save': prob_with_save,
            'prob_reduction': prob_original - prob_with_save,
            'judge_score': df_week[df_week['celebrity_name'] == celebrity_name]['judge_total'].iloc[0],
            'fan_share': df_week[df_week['celebrity_name'] == celebrity_name]['posterior_mean'].iloc[0],
        })
    
    return pd.DataFrame(results)


def plot_comparison(all_results, output_dir='figures'):
    """绘制对比图"""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. 每位明星的周级淘汰概率对比
    fig, axes = plt.subplots(2, 2, figsize=(16, 12), dpi=300)
    axes = axes.flatten()
    
    for idx, (celeb_name, celeb_info) in enumerate(CELEBRITIES.items()):
        ax = axes[idx]
        celeb_data = all_results[all_results['celebrity_name'] == celeb_name]
        
        if celeb_data.empty:
            ax.text(0.5, 0.5, f'No data for {celeb_name}', 
                   ha='center', va='center', transform=ax.transAxes)
            continue
        
        weeks = celeb_data['week'].values
        x = np.arange(len(weeks))
        width = 0.35
        
        # 绘制柱状图
        bars1 = ax.bar(x - width/2, celeb_data['prob_original'], width, 
                      label='Original Rule', color=palette_map['original'], alpha=0.8)
        bars2 = ax.bar(x + width/2, celeb_data['prob_with_save'], width,
                      label='With Judges\' Save', color=palette_map['with_save'], alpha=0.8)
        
        ax.set_xlabel('Week', fontsize=11, fontweight='bold')
        ax.set_ylabel('Elimination Probability', fontsize=11, fontweight='bold')
        ax.set_title(f'{celeb_name} (S{celeb_info["season"]}, {celeb_data["rule"].iloc[0].upper()} rule)',
                    fontsize=12, fontweight='bold', pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(weeks)
        ax.legend(frameon=False, loc='upper right')
        ax.set_ylim(0, 1.1)
        
        # 添加网格
        ax.grid(True, axis='y', linestyle=':', alpha=0.6)
        ax.grid(False, axis='x')
        
        sns.despine(ax=ax, left=False, bottom=False)
    
    plt.tight_layout()
    fig.savefig(output_dir / f'judges_save_impact_weekly_{timestamp}.png', 
                dpi=300, bbox_inches='tight')
    print(f"✓ 周级对比图已保存")
    plt.close(fig)
    
    # 2. 总体淘汰风险降低对比
    fig, ax = plt.subplots(figsize=(10, 7), dpi=300)
    
    summary = []
    for celeb_name in CELEBRITIES.keys():
        celeb_data = all_results[all_results['celebrity_name'] == celeb_name]
        if not celeb_data.empty:
            summary.append({
                'Celebrity': celeb_name,
                'Season': celeb_data['season'].iloc[0],
                'Avg Risk (Original)': celeb_data['prob_original'].mean(),
                'Avg Risk (With Save)': celeb_data['prob_with_save'].mean(),
                'Risk Reduction': celeb_data['prob_reduction'].mean(),
            })
    
    summary_df = pd.DataFrame(summary)
    
    x = np.arange(len(summary_df))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, summary_df['Avg Risk (Original)'], width,
                  label='Original Rule', color=palette_map['original'], alpha=0.8)
    bars2 = ax.bar(x + width/2, summary_df['Avg Risk (With Save)'], width,
                  label='With Judges\' Save', color=palette_map['with_save'], alpha=0.8)
    
    # 添加数值标签
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}',
                   ha='center', va='bottom', fontsize=9)
    
    ax.set_xlabel('Celebrity', fontsize=12, fontweight='bold')
    ax.set_ylabel('Average Elimination Probability', fontsize=12, fontweight='bold')
    ax.set_title('Impact of Judges\' Save on Controversial Celebrities',
                fontsize=14, fontweight='bold', pad=20, loc='left')
    ax.set_xticks(x)
    ax.set_xticklabels([f"{row['Celebrity']}\n(S{row['Season']})" 
                        for _, row in summary_df.iterrows()], fontsize=10)
    ax.legend(frameon=False, loc='upper right')
    ax.set_ylim(0, max(summary_df['Avg Risk (Original)'].max(), 
                       summary_df['Avg Risk (With Save)'].max()) * 1.2)
    
    ax.grid(True, axis='y', linestyle=':', alpha=0.6)
    ax.grid(False, axis='x')
    
    sns.despine(left=False, bottom=False)
    plt.tight_layout()
    fig.savefig(output_dir / f'judges_save_impact_summary_{timestamp}.png',
                dpi=300, bbox_inches='tight')
    print(f"✓ 总体对比图已保存")
    plt.close(fig)
    
    return summary_df


def main():
    print("=" * 60)
    print("分析 Judges' Save 对四位争议明星的影响")
    print("=" * 60)
    
    # 加载数据
    print("\n加载数据...")
    posterior, weekly = load_data()
    print(f"✓ 后验数据: {len(posterior)} 行")
    print(f"✓ 周级数据: {len(weekly)} 行")
    
    # 分析每位明星
    all_results = []
    for celeb_name, celeb_info in CELEBRITIES.items():
        result = analyze_celebrity(
            celeb_name, 
            celeb_info['season'],
            posterior,
            weekly
        )
        all_results.append(result)
    
    all_results = pd.concat(all_results, ignore_index=True)
    
    # 保存详细结果
    output_path = 'data/processed/judges_save_impact_analysis.csv'
    all_results.to_csv(output_path, index=False)
    print(f"\n✓ 详细结果已保存到: {output_path}")
    
    # 绘制对比图
    print("\n生成对比图...")
    summary_df = plot_comparison(all_results)
    
    # 打印总结
    print("\n" + "=" * 60)
    print("分析总结")
    print("=" * 60)
    print(summary_df.to_string(index=False))
    
    print("\n" + "=" * 60)
    print("关键发现")
    print("=" * 60)
    for _, row in summary_df.iterrows():
        reduction_pct = (row['Risk Reduction'] / row['Avg Risk (Original)'] * 100) if row['Avg Risk (Original)'] > 0 else 0
        print(f"\n{row['Celebrity']} (Season {int(row['Season'])}):")
        print(f"  - 原规则平均淘汰风险: {row['Avg Risk (Original)']:.3f}")
        print(f"  - 加入Save后平均风险: {row['Avg Risk (With Save)']:.3f}")
        print(f"  - 风险降低: {row['Risk Reduction']:.3f} ({reduction_pct:.1f}%)")
        
        if row['Risk Reduction'] > 0.1:
            print(f"  ⚠️ Judges' Save 显著降低了淘汰风险")
        elif row['Risk Reduction'] > 0:
            print(f"  ✓ Judges' Save 略微降低了淘汰风险")
        else:
            print(f"  → Judges' Save 对该选手影响不大")
    
    print("\n" + "=" * 60)
    print("分析完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
