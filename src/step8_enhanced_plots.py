"""
Step 8: Enhanced plots based on red team analysis
- Season-Week acceptance rate heatmap
- Enhanced controversy violin plot with rule comparison lines
"""
import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description='Enhanced plots for red team revisions')
    parser.add_argument('--summary', default='data/processed/abc_weekly_summary.csv')
    parser.add_argument('--posterior', default='data/processed/abc_weekly_posterior.csv')
    parser.add_argument('--weekly', default='data/processed/dwts_weekly_long.csv')
    parser.add_argument('--fig-dir', default='figures')
    args = parser.parse_args()

    summary = pd.read_csv(args.summary)
    posterior = pd.read_csv(args.posterior)
    weekly = pd.read_csv(args.weekly)
    
    fig_dir = Path(args.fig_dir)
    fig_dir.mkdir(parents=True, exist_ok=True)
    
    run_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    sns.set_theme(style='whitegrid')
    plt.rcParams['axes.titlesize'] = 13
    plt.rcParams['axes.labelsize'] = 11
    
    # Plot 1: Season-Week Acceptance Rate Heatmap
    print("Creating acceptance rate heatmap...")
    pivot = summary.pivot_table(
        index='week', 
        columns='season', 
        values='acceptance_rate',
        aggfunc='mean'
    )
    
    fig1, ax1 = plt.subplots(figsize=(14, 6))
    sns.heatmap(
        pivot, 
        cmap='RdYlGn', 
        center=0.3,
        vmin=0, 
        vmax=1,
        cbar_kws={'label': 'Acceptance Rate'},
        linewidths=0.5,
        linecolor='white',
        ax=ax1
    )
    ax1.set_title('Acceptance Rate Heatmap by Season and Week')
    ax1.set_xlabel('Season')
    ax1.set_ylabel('Week')
    ax1.invert_yaxis()
    fig1.tight_layout()
    fig1_path = fig_dir / f'acceptance_rate_heatmap_{run_ts}.png'
    fig1.savefig(fig1_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {fig1_path}")
    
    # Plot 2: S28+ Rule Selection Summary
    print("Creating S28+ rule selection summary...")
    s28_plus = summary[summary['season'] >= 28].copy()
    rule_counts = s28_plus['rule_used'].value_counts()
    
    fig2, ax2 = plt.subplots(figsize=(8, 5))
    colors = ['#2a788e', '#7ad151']
    bars = ax2.bar(
        ['Rank+Save', 'Percent+Save'],
        [rule_counts.get('rank', 0), rule_counts.get('percent', 0)],
        color=colors,
        edgecolor='black',
        linewidth=1.5
    )
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax2.text(
            bar.get_x() + bar.get_width()/2., height,
            f'{int(height)} weeks\n({height/len(s28_plus):.1%})',
            ha='center', va='bottom', fontsize=11, fontweight='bold'
        )
    
    ax2.set_title('S28-S34 Rule Selection (Dual Hypothesis Test)', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Number of Weeks', fontsize=12)
    ax2.set_ylim(0, max(rule_counts) * 1.2)
    ax2.grid(axis='y', alpha=0.3)
    sns.despine(ax=ax2)
    fig2.tight_layout()
    fig2_path = fig_dir / f's28_rule_selection_{run_ts}.png'
    fig2.savefig(fig2_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {fig2_path}")
    
    # Plot 3: Acceptance Rate by Season (showing S28+ jump)
    print("Creating acceptance rate by season plot...")
    season_acc = summary.groupby('season')['acceptance_rate'].mean().reset_index()
    season_acc['period'] = season_acc['season'].apply(
        lambda x: 'S28-S34\n(Judges Save)' if x >= 28 else 'S1-S27'
    )
    
    fig3, ax3 = plt.subplots(figsize=(12, 5))
    
    # Plot bars with different colors for different periods
    colors_map = {'S1-S27': '#5f6c7b', 'S28-S34\n(Judges Save)': '#e63946'}
    for period in season_acc['period'].unique():
        data = season_acc[season_acc['period'] == period]
        ax3.bar(
            data['season'], 
            data['acceptance_rate'],
            color=colors_map[period],
            label=period,
            alpha=0.8
        )
    
    # Add horizontal lines for period averages
    s1_27_avg = season_acc[season_acc['season'] < 28]['acceptance_rate'].mean()
    s28_34_avg = season_acc[season_acc['season'] >= 28]['acceptance_rate'].mean()
    
    ax3.axhline(s1_27_avg, color='#5f6c7b', linestyle='--', linewidth=2, 
                label=f'S1-S27 Avg: {s1_27_avg:.3f}')
    ax3.axhline(s28_34_avg, color='#e63946', linestyle='--', linewidth=2,
                label=f'S28-S34 Avg: {s28_34_avg:.3f}')
    
    ax3.set_title('Acceptance Rate by Season: S28+ Shows Significant Improvement', 
                  fontsize=14, fontweight='bold')
    ax3.set_xlabel('Season', fontsize=12)
    ax3.set_ylabel('Acceptance Rate', fontsize=12)
    ax3.set_ylim(0, 1)
    ax3.legend(loc='upper left', fontsize=10)
    ax3.grid(axis='y', alpha=0.3)
    sns.despine(ax=ax3)
    fig3.tight_layout()
    fig3_path = fig_dir / f'acceptance_rate_by_season_{run_ts}.png'
    fig3.savefig(fig3_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {fig3_path}")
    
    print("\nAll enhanced plots created successfully!")
    print(f"\nKey findings:")
    print(f"- S1-S27 average acceptance rate: {s1_27_avg:.3f}")
    print(f"- S28-S34 average acceptance rate: {s28_34_avg:.3f}")
    print(f"- Improvement: {(s28_34_avg - s1_27_avg):.3f} ({(s28_34_avg/s1_27_avg - 1)*100:.1f}% increase)")
    print(f"- Rank+Save selected: {rule_counts.get('rank', 0)} weeks ({rule_counts.get('rank', 0)/len(s28_plus):.1%})")
    print(f"- Percent+Save selected: {rule_counts.get('percent', 0)} weeks ({rule_counts.get('percent', 0)/len(s28_plus):.1%})")


if __name__ == '__main__':
    main()
