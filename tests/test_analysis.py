import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data_analysis as da  # noqa: E402
from lambda_function import build_results  # noqa: E402


def sample_df():
    return pd.DataFrame({
        "Diet_type": ["Paleo", "paleo ", "Vegan", "Vegan", "Keto"],
        "Recipe_name": ["A", "B", "C", "D", "E"],
        "Cuisine_type": ["american", "American", "indian", "indian", "italian"],
        "Protein(g)": [10.0, None, 5.0, 7.0, 30.0],
        "Carbs(g)": [20.0, 10.0, 0.0, 14.0, 5.0],
        "Fat(g)": [5.0, 5.0, 2.0, "bad", 40.0],
    })


def test_clean_fills_missing_and_normalises_case():
    df = da.clean_data(sample_df())
    assert df[da.NUMERIC_COLS].isna().sum().sum() == 0
    assert set(df["Diet_type"]) == {"paleo", "vegan", "keto"}


def test_average_macros():
    avg = da.average_macros(da.clean_data(sample_df()))
    assert avg.loc["vegan", "Protein(g)"] == 6.0


def test_ratios_never_infinite():
    df = da.add_ratios(da.clean_data(sample_df()))
    assert not np.isinf(df["Protein_to_Carbs_ratio"].dropna()).any()
    assert pd.isna(df.loc[df["Recipe_name"] == "C", "Protein_to_Carbs_ratio"]).all()


def test_highest_protein_diet():
    diet, _ = da.highest_protein_diet(da.average_macros(da.clean_data(sample_df())))
    assert diet == "keto"


def test_top_protein_max_five_per_diet():
    top = da.top_protein_recipes(da.clean_data(sample_df()))
    assert top.groupby("Diet_type").size().max() <= 5


def test_function_builds_nosql_document():
    doc = build_results(sample_df(), "datasets/test.csv")
    assert doc["record_count"] == 5
    assert doc["highest_protein_diet"] == "keto"
    assert len(doc["avg_macros_by_diet"]) == 3
