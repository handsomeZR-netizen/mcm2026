import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


def main() -> None:
    out = "figures/abc_vote_reconstruction_flow.png"

    fig, ax = plt.subplots(figsize=(10, 3.2), dpi=200)
    ax.set_axis_off()

    boxes = [
        ("Prior: Dirichlet(α_t)\n(weekly vote shares)", (0.03, 0.55)),
        ("Sample V^(k)\nfrom prior", (0.26, 0.55)),
        ("Simulate elimination\nunder rule R_s", (0.49, 0.55)),
        ("Compare with observed\nelimination E_obs", (0.72, 0.55)),
    ]

    box_w, box_h = 0.20, 0.28
    for text, (x, y) in boxes:
        patch = FancyBboxPatch(
            (x, y),
            box_w,
            box_h,
            boxstyle="round,pad=0.02,rounding_size=0.02",
            linewidth=1.2,
            edgecolor="#0f172a",
            facecolor="#e0f2fe",
        )
        ax.add_patch(patch)
        ax.text(
            x + box_w / 2,
            y + box_h / 2,
            text,
            ha="center",
            va="center",
            fontsize=10,
            color="#0f172a",
        )

    for i in range(len(boxes) - 1):
        x1, y1 = boxes[i][1]
        x2, y2 = boxes[i + 1][1]
        ax.add_patch(
            FancyArrowPatch(
                (x1 + box_w, y1 + box_h / 2),
                (x2, y2 + box_h / 2),
                arrowstyle="->",
                mutation_scale=12,
                linewidth=1.2,
                color="#334155",
            )
        )

    accept_box = FancyBboxPatch(
        (0.72, 0.10),
        box_w,
        0.28,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        linewidth=1.2,
        edgecolor="#14532d",
        facecolor="#dcfce7",
    )
    ax.add_patch(accept_box)
    ax.text(
        0.72 + box_w / 2,
        0.10 + 0.14,
        "Accept\n→ posterior P(V|E_obs)",
        ha="center",
        va="center",
        fontsize=10,
        color="#14532d",
    )

    reject_box = FancyBboxPatch(
        (0.49, 0.10),
        box_w,
        0.28,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        linewidth=1.2,
        edgecolor="#7f1d1d",
        facecolor="#fee2e2",
    )
    ax.add_patch(reject_box)
    ax.text(
        0.49 + box_w / 2,
        0.10 + 0.14,
        "Reject\n(resample)",
        ha="center",
        va="center",
        fontsize=10,
        color="#7f1d1d",
    )

    comp_x, comp_y = boxes[-1][1]
    ax.add_patch(
        FancyArrowPatch(
            (comp_x + box_w * 0.65, comp_y),
            (0.72 + box_w * 0.65, 0.10 + 0.28),
            arrowstyle="->",
            mutation_scale=12,
            linewidth=1.2,
            color="#14532d",
        )
    )
    ax.text(comp_x + box_w * 0.8, comp_y - 0.06, "match", fontsize=9, color="#14532d", ha="center")

    ax.add_patch(
        FancyArrowPatch(
            (comp_x + box_w * 0.35, comp_y),
            (0.49 + box_w * 0.35, 0.10 + 0.28),
            arrowstyle="->",
            mutation_scale=12,
            linewidth=1.2,
            color="#7f1d1d",
        )
    )
    ax.text(comp_x + box_w * 0.2, comp_y - 0.06, "mismatch", fontsize=9, color="#7f1d1d", ha="center")

    sample_x, sample_y = boxes[1][1]
    ax.add_patch(
        FancyArrowPatch(
            (0.49 + box_w / 2, 0.10),
            (sample_x + box_w / 2, sample_y - 0.04),
            connectionstyle="arc3,rad=-0.35",
            arrowstyle="->",
            mutation_scale=12,
            linewidth=1.0,
            color="#475569",
        )
    )

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout(pad=0)
    fig.savefig(out, transparent=False, bbox_inches="tight")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
