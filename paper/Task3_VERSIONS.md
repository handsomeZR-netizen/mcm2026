# Task3 Version Log

- 2026-01-31: Locked Task3 v1 from `paper/Task3.md` into `paper/Task3_v1.md`.
  - Figures used: task3_coef_dumbbell_20260131_164313.png, task3_coef_heatmap_20260131_164313.png, task3_coef_gap_20260131_164313.png,
    task3_pro_buff_caterpillar_20260131_164313.png, task3_cox_forest_20260131_164324.png, task3_km_fanshare_20260131_164324.png,
    task3_sensitivity_heatmap_20260131_164457.png
  - Outputs: task3_model_coefficients.csv, task3_judge_fan_consistency.csv, task3_pro_buff.csv, task3_cox_summary.csv, task3_sensitivity_summary.csv

- 2026-01-31: Created Task3 v2 (GAMM upgrade) in `paper/Task3.md`.
  - GAMM-like MixedLM with spline bases for age/week.
  - Added smooth effect plots and sensitivity heatmap.
  - Outputs tagged with _v2.

- 2026-01-31: Locked Task3 v2 from `paper/Task3.md` into `paper/Task3_v2.md` (GAMM-like spline MixedLM).

- 2026-01-31: Task3 v3 rebuilt with pyGAM (true GAM) and new outputs tagged _v3; Task3.md now points to v3.
