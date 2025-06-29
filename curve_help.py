# Refactor Plan for main_help.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import seaborn as sns
from datetime import date
from scipy.stats import percentileofscore, zscore
import os
import openpyxl
from str_cal import get_ratio, calculate_str, remove_outliers , _rolling_sumproduct , rolling_bounds_filter
from str_cal import index
import pandas as pd

##############################################################
# STUDY OVERLAYS (MA, BB, XN)
##############################################################

def moving_average(df: pd.DataFrame, window: int) -> dict:
    ma = df[::-1].rolling(window=window).mean()[::-1]
    return {
        "type": "line",
        "data": ma.iloc[0],
        "label": f"ma({window})"
    }


def median_series(df: pd.DataFrame, window: int) -> dict:
    med = df[::-1].rolling(window=window).median()[::-1]
    return {
        "type": "line",
        "data": med.iloc[0],
        "label": f"med({window})"
    }

def rolling_quantile_series(df: pd.DataFrame, window: int, quantile: float = 95) -> dict:
    quantile= quantile/100
    q_series = df[::-1].rolling(window=window).quantile(quantile)[::-1]
    return {
        "type": "line",
        "data": q_series.iloc[0],
        "label": f"rank{int(quantile * 100)}({window})"
    }


def bollinger_bands(df: pd.DataFrame, window: int, num_std: float) -> dict:
    df_rev = df[::-1]
    ma = df_rev.rolling(window=window).mean()[::-1]
    std = df_rev.rolling(window=window).std()[::-1]
    return {
        "type": "band",
        "data": {
            "ma": ma.iloc[0],
            "upper": (ma + num_std * std).iloc[0],
            "lower": (ma - num_std * std).iloc[0]
        },
        "label": f"BB({window},{num_std})"
    }


def maxmin_band(df: pd.DataFrame, window: int) -> dict:
    df_rev = df[::-1]
    return {
        "type": "band",
        "data": {
            "upper": df_rev.rolling(window=window).max()[::-1].iloc[0],
            "lower": df_rev.rolling(window=window).min()[::-1].iloc[0]
        },
        "label": f"xn({window})"
    }


##############################################################
# MATRIX COMPUTATIONS
##############################################################

str_names = index

def cal_all_str(out_curve_df, day_offset=252, lower_quantile=0.01, upper_quantile=0.99):
    out_curve_df = out_curve_df.head(day_offset + 11)
    combined_str = {}
    for str_name in str_names:
        ratio = get_ratio(str_name)
        str_df = calculate_str(out_curve_df, ratio)
        #str_df = remove_outliers(str_df, lower_quantile, upper_quantile)
        str_df= rolling_bounds_filter(str_df, window=21, k=2.5)
        combined_str[str_name] = str_df.head(day_offset)
    return combined_str


def compute_latest_percentile_ranks(data_dict: dict, lookback: int = None) -> dict:
    percentile_rank_matrix = {}
    for name, df in data_dict.items():
        ranks = {}
        for col in df.columns:
            series = df[col].dropna()
            if lookback:
                series = series.iloc[:lookback]
            if len(series) < 2:
                ranks[col] = None
                continue
            latest_value = series.iloc[0]
            rank = percentileofscore(series, latest_value, kind='rank')
            ranks[col] = round(rank, 1)
        percentile_rank_matrix[name] = pd.DataFrame([ranks]).reset_index(drop=True)
    return percentile_rank_matrix


def compute_latest_z_scores(data_dict: dict, lookback: int = None) -> dict:
    z_score_matrix = {}
    for name, df in data_dict.items():
        z_scores = {}
        for col in df.columns:
            series = df[col].dropna()
            if lookback:
                series = series.iloc[:lookback]
            if len(series) < 2:
                z_scores[col] = None
                continue
            std = series.std()
            if std == 0:
                z_scores[col] = None
            else:
                z_scores[col] = round((series.iloc[0] - series.mean()) / std, 1)
        z_score_matrix[name] = pd.DataFrame([z_scores]).reset_index(drop=True)
    return z_score_matrix


def compute_roll_down(data_dict: dict) -> dict:
    roll_down_matrix = {}
    for name, df in data_dict.items():
        latest_snapshot = df.iloc[0]
        roll_down = latest_snapshot.diff().round(1).tolist()
        roll_down_matrix[name] = pd.DataFrame([roll_down], columns=latest_snapshot.index)
    return roll_down_matrix


def compute_roll_up(data_dict: dict) -> dict:
    roll_up_matrix = {}
    for name, df in data_dict.items():
        latest_snapshot = df.iloc[0]
        roll_up = latest_snapshot.diff().round(1).tolist()
        roll_up = roll_up[1:] + [None]
        roll_up_matrix[name] = pd.DataFrame([roll_up], columns=latest_snapshot.index)
    return roll_up_matrix


def compute_ratio_matrix(data_dict: dict) -> dict:
    ratio_matrix = {}
    for name, df in data_dict.items():
        latest_snapshot = df.iloc[0]
        diffs = latest_snapshot.diff().tolist()
        ratios = [
            round(diffs[i] / diffs[i+1], 1)
            if diffs[i+1] != 0 else '∞'
            for i in range(len(diffs) - 1)
        ]
        ratio_matrix[name] = pd.DataFrame([ratios], columns=latest_snapshot[:-1].index)
    return ratio_matrix


def print_matrix(rank_matrix: dict, curve_length=15):
    printed_header = False
    for name, df in rank_matrix.items():
        if df.empty:
            continue
        row = df.iloc[0]
        if curve_length:
            row = row.iloc[:curve_length]
        if not printed_header:
            print(" ".join(row.index))
            printed_header = True
        print(name, " ".join("inf" if val == float('inf') or val == '∞' else str(val) for val in row.values))
