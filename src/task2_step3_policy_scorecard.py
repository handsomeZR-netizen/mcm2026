import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def load_metrics(path, scenario_label):
    df = pd.read_csv(path)
    df = df[['rule', 'consistency', 'FII', 'TPI']].copy()
    df['scenario'] = scenario_label
    return df


def main():
    parser = argparse.ArgumentParser(description='Task2 Step3: policy scorecard plot')
    parser.add_argument('--frozen', default='data/processed/task2_metrics_rule_default.csv')
    parser.add_argument('--dyn0', required=True)
    parser.add_argument('--dyn3', required=True)
    parser.add_argument('--out-dir', default='figures')
    parser.add_argument('--out-data', default='data/processed')
    args = parser.parse_args()

    frozen = load_metrics(args.frozen, 'Frozen')
    dyn0 = load_metrics(args.dyn0, 'Dynamic (loss=0.0)')
    dyn3 = load_metrics(args.dyn3, 'Dynamic (loss=0.3)')

    all_df = pd.concat([frozen, dyn0, dyn3], ignore_index=True)
    rule_labels = {'rank': 'Rank', 'percent': 'Percent', 'official': 'Official'}
    all_df['rule_label'] = all_df['rule'].map(rule_labels)

    # Build wide table: rows=Rule, columns=Scenario-Metric
    rows = []
    for _, row in all_df.iterrows():
        rows.append({
            'Rule': row['rule_label'],
            'Scenario': row['scenario'],
            'Consistency': row['consistency'],
            'FII': row['FII'],
            'TPI': row['TPI'],
        })
    tidy = pd.DataFrame(rows)

    wide = tidy.pivot_table(
        index='Rule',
        columns='Scenario',
        values=['Consistency', 'FII', 'TPI']
    )
    wide = wide.reindex(index=['Rank', 'Percent', 'Official'])

    # 【改进 1】展平列名，避免 MultiIndex 导致 X 轴标签混乱
    # 这会将 ('Consistency', 'Frozen') 变成 'Consistency - Frozen'
    wide.columns = [f'{metric} - {scenario}' for metric, scenario in wide.columns]

    out_data = Path(args.out_data)
    out_data.mkdir(parents=True, exist_ok=True)
    wide_path = out_data / 'task2_policy_scorecard.csv'
    wide.to_csv(wide_path)

    # Heatmap
    sns.set_theme(style='whitegrid')
    # 可以适当增加一点高度，防止纵向太挤
    fig, ax = plt.subplots(figsize=(12, 5))
    sns.heatmap(
        wide,
        cmap='crest',
        vmin=0,
        vmax=1,
        annot=True,
        fmt='.2f',
        linewidths=0.4,
        cbar_kws={'label': 'Score (higher is better)'}
    )
    ax.set_title('Policy Scorecard: Frozen vs Dynamic', fontsize=14, pad=15)
    ax.set_xlabel('Scenario', fontsize=12)
    # 【改进 2】增加 labelpad 防止 Y 轴标题 "Rule" 和刻度标签重叠
    ax.set_ylabel('Rule', labelpad=20, fontsize=12)
    ax.tick_params(axis='y', pad=8, labelsize=11)
    # 旋转 X 轴标签，防止横向重叠
    ax.tick_params(axis='x', rotation=45, labelsize=10)
    plt.setp(ax.get_xticklabels(), ha='right')
    
    # 【改进 3】移除手动的 subplots_adjust，使用 tight_layout 自动适配
    # 这一步会自动计算上下左右的边距，确保文字不重叠
    plt.tight_layout()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    fig_path = out_dir / f'task2_policy_scorecard_{run_ts}.png'
    # 【改进 4】保存时使用 bbox_inches='tight' 确保任何溢出的标签都被包进来
    fig.savefig(fig_path, dpi=300, bbox_inches='tight')

    print(str(fig_path))


if __name__ == '__main__':
    main()
