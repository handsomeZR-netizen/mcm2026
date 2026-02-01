import seaborn as sns
import matplotlib.pyplot as plt


def apply_task3_style():
    sns.set_theme(style="whitegrid")
    sns.set_context("talk", font_scale=0.9)
    plt.rcParams.update(
        {
            "figure.facecolor": "#FFFFFF",
            "axes.facecolor": "#F7F8FA",
            "grid.color": "#DADDE2",
            "axes.edgecolor": "#2B2D42",
            "axes.labelcolor": "#2B2D42",
            "xtick.color": "#2B2D42",
            "ytick.color": "#2B2D42",
            "font.family": "DejaVu Sans",
        }
    )
    palette = {
        "judge": "#2A5C82",
        "fan": "#F28F3B",
        "accent": "#7FB069",
        "muted": "#8D99AE",
    }
    return palette
