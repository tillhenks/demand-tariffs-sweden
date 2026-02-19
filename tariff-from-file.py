################################
#                              #
#  Created by Henrik Tillman   #
#                              #
#  Initial version 2026-02-19  #
#                              #
################################

import os
import pandas as pd
import matplotlib

# Headless backend
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# ========================================
# CONFIG (edit to fit your power provider)
# ========================================
price_per_kw = 90.0  # SEK per kW

WINTER_MONTHS = {11, 12, 1, 2, 3} # Only these moths will be used for the calcualtion, summer is free
NIGHT_HOURS = set(range(22, 24)) | set(range(0, 6)) # If some hourse are free, adjust accordingly
TOP_N = 3                         # Option B: avg of top N daily peaks per month

CSV_PATH = "consumption.csv"
OUTPUT_DIR = "output"
PDF_REPORT_PATH = os.path.join(OUTPUT_DIR, "demand_tariff_report.pdf")

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ========
# LOAD CSV
# ========
df = pd.read_csv(
    CSV_PATH,
    sep=";",
    header=None,
    names=["ts", "kw"],
    encoding="utf-8"
)

df["ts"] = pd.to_datetime(df["ts"], format="%Y-%m-%d %H:%M", errors="raise")
df["kw"] = df["kw"].astype(str).str.replace(",", ".", regex=False).astype(float)

df["year"]  = df["ts"].dt.year
df["month"] = df["ts"].dt.month
df["hour"]  = df["ts"].dt.hour
df["date"]  = df["ts"].dt.date
df["month_period"] = df["ts"].dt.to_period("M")

# ==========================
# FILTER TO CHARGEABLE HOURS
# ==========================
chargeable = df[
    (df["month"].isin(WINTER_MONTHS)) &
    (~df["hour"].isin(NIGHT_HOURS))
].copy()

if chargeable.empty:
    raise ValueError("No rows left after filtering. Check WINTER_MONTHS / NIGHT_HOURS and CSV contents.")

# ===============
# DAILY PEAK (kW)
# ===============
daily_peak = (
    chargeable.groupby(["year", "month_period", "date"], as_index=False)["kw"].max()
    .rename(columns={"kw": "daily_peak_kw"})
)

# ====================
# MONTHLY METRICS (kW)
# ====================

# Option A: average of daily peaks in the month
optA_kw = daily_peak.groupby(["year", "month_period"])["daily_peak_kw"].mean().rename("optA_kw")

# Option B: average of the TOP_N daily peaks in the month
optB_kw = daily_peak.groupby(["year", "month_period"])["daily_peak_kw"].apply(
    lambda s: s.nlargest(min(TOP_N, len(s))).mean()
).rename("optB_kw")

# Option C: single highest (max) daily peak in the month
optC_kw = daily_peak.groupby(["year", "month_period"])["daily_peak_kw"].max().rename("optC_kw")

# ======================================================
# OPTION C: EXACT TIMESTAMP THAT CAUSED THE MONTHLY PEAK
# ======================================================
idx = chargeable.groupby(["year", "month_period"])["kw"].idxmax()
optC_timestamp = chargeable.loc[idx, ["year", "month_period", "ts", "kw"]].rename(columns={
    "ts": "optC_peak_timestamp",
    "kw": "optC_peak_kw_hourly"
})

# =====================
# MONTHLY SUMMARY TABLE
# =====================
summary = pd.concat([optA_kw, optB_kw, optC_kw], axis=1).reset_index()
summary = summary.merge(
    optC_timestamp[["year", "month_period", "optC_peak_timestamp"]],
    on=["year", "month_period"],
    how="left"
)

summary["optA_cost_kr"] = summary["optA_kw"] * price_per_kw
summary["optB_cost_kr"] = summary["optB_kw"] * price_per_kw
summary["optC_cost_kr"] = summary["optC_kw"] * price_per_kw

summary["month"] = summary["month_period"].astype(str)

# For ordering/plotting: a real timestamp for each month (start of month)
summary["month_ts"] = summary["month_period"].dt.to_timestamp()

# Print to console (full precision)
print("\n=== Monthly Summary (all years) ===")
print(summary.sort_values(["year", "month_period"]).to_string(index=False))

# =============
# YEARLY TOTALS
# =============
yearly_costs = summary.groupby("year", as_index=False).agg(
    optA_total_cost_kr=("optA_cost_kr", "sum"),
    optB_total_cost_kr=("optB_cost_kr", "sum"),
    optC_total_cost_kr=("optC_cost_kr", "sum"),
).round(2)

print("\n=== Yearly Totals (kr) ===")
print(yearly_costs.to_string(index=False))

grand_totals = yearly_costs[["optA_total_cost_kr", "optB_total_cost_kr", "optC_total_cost_kr"]].sum().round(2)
print("\n=== Grand Totals Across All Years (kr) ===")
print(f"Option A: {grand_totals['optA_total_cost_kr']:.2f}")
print(f"Option B: {grand_totals['optB_total_cost_kr']:.2f}")
print(f"Option C: {grand_totals['optC_total_cost_kr']:.2f}")

# ==================================================
# TOP 10 WORST PEAK HOURS PER YEAR (AFTER FILTERING)
# ==================================================
top10_per_year = (
    chargeable.sort_values(["year", "kw", "ts"], ascending=[True, False, True])
    .groupby("year", as_index=False)
    .head(10)
    .copy()
)

print("\n=== Top 10 Worst Peak Hours PER YEAR (after filters) ===")
for y in sorted(top10_per_year["year"].unique()):
    print(f"\n-- {y} --")
    subset = top10_per_year[top10_per_year["year"] == y]
    print(subset[["ts", "kw"]].to_string(index=False))

# ===================================
# HELPERS: render tables as PDF pages
# ===================================
def df_to_table_figure(dataframe: pd.DataFrame, title: str, max_rows: int = 35):
    """
    Render a dataframe as a matplotlib table on a single figure page.
    If the dataframe is long, it truncates to max_rows.
    """
    df_show = dataframe.copy()
    if len(df_show) > max_rows:
        df_show = df_show.head(max_rows).copy()
        title = f"{title} (showing first {max_rows} rows of {len(dataframe)})"

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.set_title(title)

    # Convert everything to strings for stable table rendering
    cell_text = df_show.astype(str).values.tolist()
    col_labels = list(df_show.columns)

    tbl = ax.table(
        cellText=cell_text,
        colLabels=col_labels,
        loc="center"
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    tbl.scale(1, 1.2)

    fig.tight_layout()
    return fig

# ========================================
# PLOTTING (SAVE PNGs + EXPORT PDF REPORT)
# ========================================
# Save per-year PNGs (as before) + combined PNG, and build a PDF containing:
# - Tables: yearly totals, monthly summary (maybe truncated), top10 per year (per year pages)
# - Combined plot
# - Per-year plots

# Ensure chronological ordering for plots
summary_sorted_all = summary.sort_values(["month_ts"]).copy()

# Build PDF report
with PdfPages(PDF_REPORT_PATH) as pdf:

    # ---- Page 1: Yearly totals table
    fig = df_to_table_figure(yearly_costs, "Yearly Totals (kr)")
    pdf.savefig(fig)
    plt.close(fig)

    # ---- Page 2: Monthly summary table (key columns)
    monthly_table = summary.sort_values(["year", "month_period"])[
        ["year", "month", "optA_kw", "optA_cost_kr", "optB_kw", "optB_cost_kr", "optC_kw", "optC_cost_kr", "optC_peak_timestamp"]
    ].copy()
    fig = df_to_table_figure(monthly_table, "Monthly Summary (kW + kr + Option C timestamp)", max_rows=30)
    pdf.savefig(fig)
    plt.close(fig)

    # ---- Combined plot across ALL years (one figure)
    plt.figure()
    plt.plot(summary_sorted_all["month_ts"], summary_sorted_all["optA_cost_kr"], marker="o", label="Option A")
    plt.plot(summary_sorted_all["month_ts"], summary_sorted_all["optB_cost_kr"], marker="o", label="Option B")
    plt.plot(summary_sorted_all["month_ts"], summary_sorted_all["optC_cost_kr"], marker="o", label="Option C")
    plt.ylabel("Cost (kr)")
    plt.title("Monthly Effect Cost Comparison (A/B/C) — All Years")
    plt.legend()
    plt.tight_layout()

    combined_png = os.path.join(OUTPUT_DIR, "effect_costs_all_years.png")
    plt.savefig(combined_png, dpi=300)
    pdf.savefig()  # saves the current figure into the PDF
    plt.close()

    print(f"Saved combined plot: {combined_png}")

    # ---- Top 10 per year pages (and also save a CSV per year if you want later)
    for y in sorted(top10_per_year["year"].unique()):
        subset = top10_per_year[top10_per_year["year"] == y][["ts", "kw"]].copy()
        subset = subset.rename(columns={"ts": "timestamp", "kw": "kw_that_hour"})
        fig = df_to_table_figure(subset, f"Top 10 Worst Peak Hours — {y}", max_rows=10)
        pdf.savefig(fig)
        plt.close(fig)

    # ---- Per-year plots + save PNGs
    for y in sorted(summary["year"].unique()):
        plot_df = summary[summary["year"] == y].copy().sort_values("month_period")

        plt.figure()
        plt.plot(plot_df["month"], plot_df["optA_cost_kr"], marker="o", label="Option A")
        plt.plot(plot_df["month"], plot_df["optB_cost_kr"], marker="o", label="Option B")
        plt.plot(plot_df["month"], plot_df["optC_cost_kr"], marker="o", label="Option C")
        plt.xticks(rotation=45, ha="right")
        plt.ylabel("Cost (kr)")
        plt.title(f"Monthly Effect Cost Comparison (A/B/C) — {y}")
        plt.legend()
        plt.tight_layout()

        filename = os.path.join(OUTPUT_DIR, f"effect_costs_{y}.png")
        plt.savefig(filename, dpi=300)
        pdf.savefig()  # add the same figure to the PDF
        plt.close()

        print(f"Saved plot: {filename}")

print(f"Saved PDF report: {PDF_REPORT_PATH}")

