import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def parse_list(value: str):
    parts = [p.strip() for p in value.split(',') if p.strip()]
    return parts


def main():
    parser = argparse.ArgumentParser(description='Task2 Step3: custom storyline plot')
    parser.add_argument('--survival', required=True, help='Path to dynamic survival weekly csv')
    parser.add_argument('--contestants', required=True, help='Comma-separated list of contestants')
    parser.add_argument('--tag', default='custom')
    parser.add_argument('--focus-season', type=int, default=27)
    parser.add_argument('--out-dir', default='figures')
    args = parser.parse_args()

    df = pd.read_csv(args.survival)
    contestants = parse_list(args.contestants)

    df = df[df['celebrity_name'].isin(contestants)].copy()
    if df.empty:
        raise SystemExit('No rows for selected contestants')

    rule_labels = {'rank': 'Rank', 'percent': 'Percent', 'official': 'Official'}
    df['rule_label'] = df['rule'].map(rule_labels)

    sns.set_theme(style='whitegrid')
    palette = sns.color_palette('mako', n_colors=len(contestants))

    g = sns.relplot(
        data=df,
        x='week', y='survival_prob',
        hue='celebrity_name', col='rule_label',
        kind='line', height=3.1, aspect=1.15,
        palette=palette, facet_kws=dict(sharey=True)
    )
    g.set_axis_labels('Week', 'Survival Probability')
    g.set_titles('{col_name}')
    g._legend.set_title('Contestant')
    g.fig.suptitle(f'Season {args.focus_season} Storyline (Selected Contestants)', y=1.04)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    fig_path = out_dir / f'task2_storyline_selected_s{args.focus_season}_{args.tag}_{run_ts}.png'
    g.savefig(fig_path, dpi=300)

    print(str(fig_path))


if __name__ == '__main__':
    main()
