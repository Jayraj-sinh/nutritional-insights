"""
Task 1 - Dataset Analysis & Insights
Cloud-Native Nutritional Insights Application

Usage:
    python data_analysis.py                     # uses data/All_Diets.csv
    python data_analysis.py path/to/file.csv    # custom path
Outputs (charts + CSV results) are written to ./outputs/
"""
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

NUMERIC_COLS = ["Protein(g)", "Carbs(g)", "Fat(g)"]
TEXT_COLS = ["Diet_type", "Recipe_name", "Cuisine_type"]
DEFAULT_CSV = os.getenv("DATA_PATH", os.path.join("data", "All_Diets.csv"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")


# ---------------------------------------------------------------- loading
def load_data(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        sys.exit(f"[ERROR] Dataset not found at '{path}'. Download All_Diets.csv into ./data/")
    df = pd.read_csv(path)
    print(f"[INFO] Loaded {len(df):,} rows and {len(df.columns)} columns from {path}")
    return df


# ---------------------------------------------------------------- cleaning
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Fix column names, normalise text, coerce numbers, fill missing values with the mean."""
    df = df.copy()
    df.columns = df.columns.str.strip()

    for col in TEXT_COLS:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    # The dataset mixes 'Paleo' and 'paleo', 'mexican' and 'Mexican' etc.
    df["Diet_type"] = df["Diet_type"].str.lower()
    df["Cuisine_type"] = df["Cuisine_type"].str.lower()

    # Force numeric (bad strings -> NaN) then fill NaN with the column mean.
    # NOTE: the pseudocode's df.fillna(df.mean()) crashes on text columns in
    # pandas 2.x, so we only take the mean of the numeric columns.
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    missing_before = int(df[NUMERIC_COLS].isna().sum().sum())
    df[NUMERIC_COLS] = df[NUMERIC_COLS].fillna(df[NUMERIC_COLS].mean())

    df = df.dropna(subset=["Diet_type"])
    df = df.drop_duplicates()
    print(f"[INFO] Filled {missing_before} missing macro values; {len(df):,} rows after cleaning")
    return df


# ---------------------------------------------------------------- analysis
def average_macros(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("Diet_type")[NUMERIC_COLS].mean().round(2)


def top_protein_recipes(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    return (df.sort_values("Protein(g)", ascending=False)
              .groupby("Diet_type")
              .head(n)
              .sort_values(["Diet_type", "Protein(g)"], ascending=[True, False])
              [["Diet_type", "Recipe_name", "Cuisine_type", "Protein(g)"]])


def highest_protein_diet(avg_macros: pd.DataFrame) -> tuple:
    diet = avg_macros["Protein(g)"].idxmax()
    return diet, float(avg_macros.loc[diet, "Protein(g)"])


def most_common_cuisines(df: pd.DataFrame) -> pd.DataFrame:
    counts = df.groupby(["Diet_type", "Cuisine_type"]).size().reset_index(name="Recipe_count")
    idx = counts.groupby("Diet_type")["Recipe_count"].idxmax()
    return counts.loc[idx].reset_index(drop=True)


def add_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """Protein:Carbs and Carbs:Fat ratios. A zero denominator gives NaN instead of infinity."""
    df = df.copy()
    df["Protein_to_Carbs_ratio"] = (df["Protein(g)"] / df["Carbs(g)"].replace(0, np.nan)).round(3)
    df["Carbs_to_Fat_ratio"] = (df["Carbs(g)"] / df["Fat(g)"].replace(0, np.nan)).round(3)
    return df


# ---------------------------------------------------------------- visuals
def make_charts(df, avg_macros, top_protein, out_dir=OUTPUT_DIR):
    # Imported here so the serverless function (which reuses this module)
    # does not pay the matplotlib start-up cost -> faster cold start.
    import matplotlib
    matplotlib.use("Agg")  # no screen inside Docker / CI
    import matplotlib.pyplot as plt
    import seaborn as sns

    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sns.set_theme(style="whitegrid")

    # 1. Bar chart - average macros per diet
    long = avg_macros.reset_index().melt(id_vars="Diet_type", var_name="Macronutrient", value_name="Grams")
    plt.figure(figsize=(10, 6))
    sns.barplot(data=long, x="Diet_type", y="Grams", hue="Macronutrient")
    plt.title(f"Average Macronutrients by Diet Type  (generated {stamp})")
    plt.ylabel("Average grams per recipe"); plt.xlabel("Diet type")
    plt.tight_layout(); plt.savefig(os.path.join(out_dir, "bar_avg_macros.png"), dpi=120); plt.close()

    # 2. Heatmap - macro content vs diet type
    plt.figure(figsize=(8, 5))
    sns.heatmap(avg_macros, annot=True, fmt=".1f", cmap="YlOrRd")
    plt.title(f"Macronutrient Heatmap by Diet Type  ({stamp})")
    plt.tight_layout(); plt.savefig(os.path.join(out_dir, "heatmap_macros.png"), dpi=120); plt.close()

    # 3. Scatter - top 5 protein recipes per diet across cuisines
    plt.figure(figsize=(11, 6))
    sns.scatterplot(data=top_protein, x="Cuisine_type", y="Protein(g)", hue="Diet_type", s=120)
    plt.title(f"Top 5 Protein-Rich Recipes per Diet, by Cuisine  ({stamp})")
    plt.xticks(rotation=30, ha="right")
    plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout(); plt.savefig(os.path.join(out_dir, "scatter_top_protein.png"), dpi=120); plt.close()

    # Bonus: correlation heatmap between the macros
    plt.figure(figsize=(6, 5))
    sns.heatmap(df[NUMERIC_COLS].corr(), annot=True, cmap="coolwarm", vmin=-1, vmax=1)
    plt.title(f"Macro Correlation  ({stamp})")
    plt.tight_layout(); plt.savefig(os.path.join(out_dir, "heatmap_correlation.png"), dpi=120); plt.close()
    print(f"[INFO] Charts saved to ./{out_dir}/")


# ---------------------------------------------------------------- main
def main(path=DEFAULT_CSV):
    print("=" * 70)
    print(f" Nutritional Insights - run started {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 70)

    df = clean_data(load_data(path))
    df = add_ratios(df)

    avg = average_macros(df)
    top5 = top_protein_recipes(df)
    best_diet, best_val = highest_protein_diet(avg)
    cuisines = most_common_cuisines(df)

    pd.set_option("display.width", 140, "display.max_colwidth", 50)
    print("\n--- Average macronutrients per diet type ---\n", avg)
    print("\n--- Top 5 protein-rich recipes per diet type ---\n", top5.to_string(index=False))
    print(f"\n--- Diet with highest average protein: {best_diet} ({best_val:.2f} g) ---")
    print("\n--- Most common cuisine per diet type ---\n", cuisines.to_string(index=False))
    print("\n--- Sample of new ratio metrics ---\n",
          df[["Recipe_name", "Protein_to_Carbs_ratio", "Carbs_to_Fat_ratio"]].head(10).to_string(index=False))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    avg.to_csv(os.path.join(OUTPUT_DIR, "avg_macros.csv"))
    top5.to_csv(os.path.join(OUTPUT_DIR, "top5_protein.csv"), index=False)
    cuisines.to_csv(os.path.join(OUTPUT_DIR, "common_cuisines.csv"), index=False)
    df.to_csv(os.path.join(OUTPUT_DIR, "cleaned_with_ratios.csv"), index=False)

    make_charts(df, avg, top5)
    print(f"\n[DONE] Finished at {datetime.now():%Y-%m-%d %H:%M:%S}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV)
