from str_cal import  rolling_bounds_filter,fill_missing_values,load_data, index, get_ratio, rolling_iqr_filter
import pandas as pd
import numpy as np
from scipy.stats import percentileofscore
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from scipy.stats import percentileofscore
from dash import dcc, html
from kde_help import get_rank
from str_cal import process_series


 # removed rest unconventional structures

###### build button##########################################################

def get_button_class_tab7(is_active: bool) -> str:
    base = "tab7-button me-2"
    return base + " selected" if is_active else base

def build_button_tab7(label, id, active=False):
    return dbc.Button(
        label,
        id=id,
        className=get_button_class_tab7(active), 
        n_clicks=0
    )

####################### df computation ###############################################
#structure_names= {"D12"}
structure_names= index

def handle_outliers(series: pd.Series, window_size: int, threshold: float, method: str = 'replace') -> pd.Series:
    if not isinstance(series, pd.Series):
        raise TypeError("Input 'series' must be a pandas.Series.")
        
    # --- Step 1: Calculate rolling statistics for the PRECEDING window ---
    
    # Rolling median of the window *before* each point
    # We use shift(1) to ensure each point is compared against the stats of the window that came before it.
    rolling_median = series.rolling(window=window_size, min_periods=3, center=False).median().shift(1)

    # Rolling MAD (Median Absolute Deviation)
    def mad(window):
        median = np.median(window)
        return np.median(np.abs(window - median))

    # .apply() is used here as pandas has no built-in rolling mad
    rolling_mad = series.rolling(window=window_size, min_periods=1, center=False).apply(mad, raw=True).shift(1)
    
    # --- Step 2: Calculate the modified Z-score for each point ---
    
    # The constant 1.4826 scales MAD to be comparable to standard deviation
    # We handle cases where rolling_mad is 0 to avoid division by zero errors
    with np.errstate(divide='ignore', invalid='ignore'):
        score = np.abs(series - rolling_median) / (1.4826 * rolling_mad)
    
    # If rolling_mad was 0, the score is NaN/inf. We can treat these as non-outliers (score=0)
    # as a zero-deviation window means the point should be identical to the median.
    score.fillna(0, inplace=True)
    
    # --- Step 3: Identify outliers based on the score and threshold ---
    is_outlier = score > threshold
    
    # --- Step 4: Handle the outliers based on the chosen method ---
    if method == 'replace':
        series_cleaned = series.copy()
        # Replace outliers with the median of the preceding window
        series_cleaned[is_outlier] = rolling_median[is_outlier]
        return series_cleaned
        
    elif method == 'identify':
        return is_outlier
        
    elif method == 'remove':
        return series[~is_outlier]
        
    else:
        raise ValueError("Method must be one of 'replace', 'identify', or 'remove'.")



def compute_3d_structure(out_df: pd.DataFrame, structure_names= structure_names , local_win=21, curve_length=20 ) -> pd.DataFrame:
    """
    Efficiently compute a MultiIndex DataFrame with shape (Date, Structure, Contract).
    - Z axis: Dates (depth)
    - X axis: Structure names
    - Y axis: Contracts
    - Values: Weighted structure results
    
    Returns a long-form pandas DataFrame with a MultiIndex.
    """
    if out_df.empty:
        return pd.DataFrame(columns=["Value"]).set_index(["Date", "Structure", "Contract"])
    
    all_frames = []  # Temporary list to store DataFrames for each structure
    dates = out_df.index[: min(local_win, len(out_df))] # Only use local window of most recent dates
    contracts = out_df.columns.to_numpy()         # All contract labels, e.g., ['EDU5', 'EDZ5', ...]
    n_contracts = len(contracts)
    curve_length = min(curve_length, n_contracts)
    rows = out_df.loc[dates].to_numpy()
    records = []

    # Loop over each structure (e.g., L3, L6, L12...)
    for struct in structure_names:
        weights = np.array(get_ratio(struct))
        n = len(weights)

        # Skip if structure size > available contracts
        if n > n_contracts:
            continue

        for d_idx, date in enumerate(dates):
            # Outlier handling ONCE at row level
            row_series = pd.Series(rows[d_idx], index=contracts)
            row = handle_outliers(series=row_series,
                                  window_size=10,
                                  threshold=3.0,
                                  method='replace').to_numpy()

            # Convolution (sliding dot product)
            conv = np.convolve(row, weights[::-1], mode="valid") * 100
            result = np.full(n_contracts, np.nan)
            result[: len(conv)] = conv

            # Trim safely
            series_trimmed = pd.Series(result, index=contracts).iloc[:curve_length]

            # Store as records
            records.extend(
                {"Date": date, "Structure": struct, "Contract": c, "Value": v}
                for c, v in zip(series_trimmed.index, series_trimmed.values)
            )

    if not records:
        return pd.DataFrame(columns=["Value"]).set_index(["Date", "Structure", "Contract"])

    final_df = pd.DataFrame.from_records(records)
    return final_df.set_index(["Date", "Structure", "Contract"])


def compute_percentile_df(str_data_3d: pd.DataFrame) -> pd.DataFrame:
    """
    Compute percentile rank of latest values vs their full historical distribution.
    Returns MultiIndex DataFrame: (Structure, Contract) -> Percentile
    """
    if str_data_3d.empty:
        return pd.DataFrame(columns=["Value"]).set_index(["Structure", "Contract"])

    # Get the latest available date safely
    latest_date = str_data_3d.index.get_level_values("Date").max()

    try:
        latest_df = str_data_3d.xs(latest_date, level="Date")
    except KeyError:
        return pd.DataFrame(columns=["Value"]).set_index(["Structure", "Contract"])

    results = {}

    # Group by (Structure, Contract) once for efficiency
    grouped = str_data_3d.groupby(level=["Structure", "Contract"])

    for (structure, contract), latest_row in latest_df.iterrows():
        latest_value = latest_row["Value"]

        if pd.isna(latest_value):
            results[(structure, contract)] = None
            continue

        try:
            # Full series for this (structure, contract) across time
            series = grouped.get_group((structure, contract))["Value"].dropna()
            if series.empty:
                results[(structure, contract)] = None
            else:
                percentile = percentileofscore(series, latest_value, kind="mean")
                results[(structure, contract)] = percentile
        except KeyError:
            results[(structure, contract)] = None  # missing history

    # Build final DataFrame with explicit MultiIndex
    percentile_rank_df = pd.DataFrame.from_dict(results, orient="index", columns=["Value"])
    percentile_rank_df.index = pd.MultiIndex.from_tuples(
        percentile_rank_df.index, names=["Structure", "Contract"]
    )

    return percentile_rank_df





def compute_risk_reward_roll_df(latest_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Ensure proper index naming
    latest_df = latest_df.copy()
    latest_df.index.names = ["Structure", "Contract"]

    # Shift values per Structure
    latest_df["Prev"] = latest_df.groupby("Structure")["Value"].shift(1)
    latest_df["Next"] = latest_df.groupby("Structure")["Value"].shift(-1)

    # Roll down = current - prev
    roll_down_value = latest_df["Prev"]- latest_df["Value"]
    conditions = [
        roll_down_value > 0,
        roll_down_value < 0,
        roll_down_value == 0
    ]

    choices = [
        "▲" + roll_down_value.abs().round(1).astype(str),
        "▼" + roll_down_value.abs().round(1).astype(str),
        "0.0" 
    ]

    roll_down = pd.Series(
        np.select(conditions, choices, default=""), 
        index=roll_down_value.index
    )

    # Roll up = current - next
    roll_up_value =  latest_df["Next"] - latest_df["Value"]
    conditions = [
        roll_up_value > 0,
        roll_up_value < 0,
        roll_up_value == 0
    ]

    choices = [
        "▲" + roll_up_value.abs().round(1).astype(str),
        "▼" + roll_up_value.abs().round(1).astype(str),
        "0.0" 
    ]

    roll_up = pd.Series(
        np.select(conditions, choices, default=""), 
        index=roll_up_value.index
    ) # preserve index
    # Initialize outputs
    rr = pd.Series(np.nan, index=latest_df.index, dtype="object")
    rrdiff = pd.Series(np.nan, index=latest_df.index, dtype="object")

    # Valid rows (have both prev & next)
    mask_valid = latest_df["Prev"].notna() & latest_df["Next"].notna()

    if mask_valid.any():
        rd = roll_down_value[mask_valid]
        ru = roll_up_value[mask_valid]
        abs_rd, abs_ru = rd.abs(), ru.abs()

        # Valley
        is_valley = (rd > 0) & (ru >= 0)
        rr.loc[is_valley.index[is_valley]] = "▲99"
        rrdiff.loc[is_valley.index[is_valley]] = "▲" + np.minimum(abs_rd[is_valley], abs_ru[is_valley]).round(1).astype(str)

        # Peak
        is_peak = (rd < 0) & (ru <= 0)
        rr.loc[is_peak.index[is_peak]] =  "▼99"
        rrdiff.loc[is_peak.index[is_peak]] = "▼"+ np.minimum(abs_rd[is_peak], abs_ru[is_peak]).round(1).astype(str)

        # Mixed
        is_mixed = ~(is_valley | is_peak)
        if is_mixed.any():
            rd_m, ru_m = rd[is_mixed], ru[is_mixed]
            abs_rd_m, abs_ru_m = abs_rd[is_mixed], abs_ru[is_mixed]

            # Arrow sign
            arrow = np.where(
                abs_rd_m > abs_ru_m,
                np.where(rd_m > 0, "▲", "▼"),
                np.where(ru_m > 0, "▲", "▼"),
            )

            # RR diff
            diff_val = (abs_rd_m - abs_ru_m).abs().round(1).astype(str)
            rrdiff.loc[rd_m.index] = np.core.defchararray.add(arrow, diff_val)

            # Risk/reward ratio
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = np.where(
                    (abs_rd_m == 0) | (abs_ru_m == 0),
                    99,
                    np.minimum(99, np.maximum(abs_rd_m, abs_ru_m) / np.minimum(abs_rd_m, abs_ru_m))
                )
            rr.loc[rd_m.index] = np.core.defchararray.add(arrow, np.abs(ratio).round(1).astype(str))

    # Helper to return aligned DataFrames
    def make_df(series):
        return pd.DataFrame(series.rename("Value"))

    return (
        make_df(rr),
        make_df(rrdiff),
        make_df(roll_down),
        make_df(roll_up),
    )



def compute_zscore_df(str_data_3d: pd.DataFrame) -> pd.DataFrame:
    if str_data_3d.empty:
        return pd.DataFrame(columns=["Value"])

    # Ensure proper index levels
    str_data_3d = str_data_3d.copy()
    str_data_3d.index.names = ["Date", "Structure", "Contract"]

    # --- Step 1: find latest date
    try:
        latest_date = str_data_3d.index.get_level_values("Date").max()
    except Exception as e:
        print(f"[ERROR] Could not extract latest_date: {e}")
        return pd.DataFrame(columns=["Value"])

    latest_df = str_data_3d.xs(latest_date, level="Date")

    # --- Step 2: compute mean & std per (Structure, Contract)
    stats = (
        str_data_3d.groupby(["Structure", "Contract"])["Value"]
        .agg(["mean", "std"])
        .rename(columns={"mean": "mu", "std": "sigma"})
    )

    # --- Step 3: align with latest_df
    merged = latest_df[["Value"]].join(stats, how="left")

    # --- Step 4: compute z-score safely
    def safe_zscore(row):
        val, mu, sigma = row["Value"], row["mu"], row["sigma"]
        if pd.isna(val) or pd.isna(sigma) or sigma == 0:
            return np.nan
        return (val - mu) / sigma

    merged["ZScore"] = merged.apply(safe_zscore, axis=1)

    # --- Step 5: return only ZScore in expected shape
    zscore_df = merged[["ZScore"]].rename(columns={"ZScore": "Value"})
    zscore_df.index.names = ["Structure", "Contract"]

    return zscore_df


def compute_range_df(str_data_3d):
    try:
        # latest date in dataset
        latest_date = str_data_3d.index.get_level_values("Date").unique()[0]
        latest_df = str_data_3d.loc[(latest_date)]
    except Exception as e:
        print(f"[ERROR] Could not extract latest_date: {e}")
        return pd.DataFrame(columns=["Value"])

    range_df = {}
    for (structure, contract), _ in latest_df.iterrows():
        try:
            series = (str_data_3d.xs((structure, contract), level=("Structure", "Contract"))["Value"]
                .dropna())

            if series.empty:
                rng_val = None
            else:
                s_min, s_max = series.min(), series.max()
                if pd.isna(s_min) or pd.isna(s_max):
                    rng_val = None
                else:
                    rng_val = s_max - s_min

            range_df[(structure, contract)] = rng_val

        except KeyError:
            range_df[(structure, contract)] = None
        except Exception as e:
            print(f"[ERROR] {structure}-{contract}: {e}")
            range_df[(structure, contract)] = None

    # final DataFrame
    range_df = pd.DataFrame.from_dict(range_df, orient="index", columns=["Value"])
    range_df.index = pd.MultiIndex.from_tuples(
        range_df.index, names=["Structure", "Contract"]
    )
    return range_df


def classify_regime_in_series(str_data_3d, bb_k=2, window=21):
    """
    BB/ATR-based regime classifier for last 21-day series.

    Breakout:
    Latest value is above the upper Bollinger Band or below the lower band, or
    Daily move exceeds 2× ATR (volatility spike).

    Trend: If not a breakout, the slope of the 21-day series is non-zero:

    Slope magnitude > threshold → Strong trend
    Slope magnitude ≤ threshold → Weak trend
    Direction = Up if slope > 0, Down if slope < 0

    Range: If not a breakout and slope is near zero → classified as Range.
    """
    regimes = {}

    try:
        latest_date = str_data_3d.index.get_level_values("Date").max()
        latest_df = str_data_3d.loc[latest_date]
    except Exception as e:
        print(f"[ERROR] Could not extract latest_date: {e}")
        return pd.DataFrame(columns=["Value"])

    regime_code_map={
        "Breakout": "⚡", # "★"
        "Range": "↔",
        "Trend_Weak_Up": "↑",
        "Trend_Weak_Down": "↓",
        "Trend_Strong_Up": "↑↑",
        "Trend_Strong_Down": "↓↓",
    }

    for (structure, contract), _ in latest_df.iterrows():
        try:
            # Historical series for this structure/contract
            series = str_data_3d.xs((structure, contract), level=("Structure", "Contract"))["Value"].dropna()

            if series.empty or len(series) < 2:
                regimes[(structure, contract)] = None
                continue

            # Take last `window` points
            series = series.tail(window)

            # Bollinger Bands
            mean_val = series.mean()
            std_val = series.std(ddof=0)
            upper_bb = mean_val + bb_k * std_val
            lower_bb = mean_val - bb_k * std_val

            # ATR proxy
            daily_diff = series.diff().abs()
            atr = daily_diff.mean()

            # Latest values
            last_close = series.iloc[-1]
            prev_close = series.iloc[-2]
            last_move = abs(last_close - prev_close)

            # Slope
            x = np.arange(len(series))
            y = series.values
            slope, _ = np.polyfit(x, y, 1)

            # Classification
            if np.isnan(last_close) or np.isnan(upper_bb) or np.isnan(lower_bb) or np.isnan(atr):
                regime = None
            elif (last_close > upper_bb) or (last_close < lower_bb) or (last_move > 2 * atr):
                regime = "Breakout"
            else:
                slope_threshold = std_val / len(series) if std_val > 0 else 1e-6
                if abs(slope) < slope_threshold:
                    regime = "Range"
                else:
                    strength = "Strong" if abs(slope) > 2 * slope_threshold else "Weak"
                    direction = "Up" if slope > 0 else "Down"
                    regime = f"Trend_{strength}_{direction}"

            
            #regimes[(structure, contract)] = regime
            regimes[(structure, contract)] = regime_code_map.get(regime, np.nan)
        except KeyError:
            regimes[(structure, contract)] = None
        except Exception as e:
            print(f"[ERROR] {structure}-{contract}: {e}")
            regimes[(structure, contract)] = None

    # Final DataFrame with column named 'Value' for heatmap compatibility
    regime_df = pd.DataFrame.from_dict(regimes, orient="index", columns=["Value"])
    regime_df.index = pd.MultiIndex.from_tuples(
        regime_df.index, names=["Structure", "Contract"]
    )

    return regime_df



# str_data_3d= compute_3d_structure(out_df, structure_names, local_win=21, curve_length=20)
# latest_date = str_data_3d.index.get_level_values("Date").unique()[0]
# latest_df = str_data_3d.loc[(latest_date)]
# risk_reward_df, risk_reward_diff_df, roll_down_df = compute_risk_reward_roll_df(latest_df)
# percentile_rank_df= compute_percentile_df(str_data_3d)
# print(percentile_rank_df)



#################################visualisation ####################################################################
# # Count them
# dates = str_data_3d.index.get_level_values("Date").unique()
# structures = str_data_3d.index.get_level_values("Structure").unique()
# contracts = str_data_3d.index.get_level_values("Contract").unique()
# print(dates)
# print("latest date", dates[0])
# print(structures)
# print(contracts)
# print("Number of Dates:", len(dates))  # along Z
# print("Number of Structures:", len(structures)) # along Y
# print("Number of Contracts:", len(contracts)) # along x
# print("latest_df", str_data_3d.loc[(latest_date)]
# #accessing 
# # str_data_3d.loc["2024-06-01"] # at any date
# # str_data_3d.loc[("2024-06-01", "L6")] # a structure at any date
# # str_data_3d.loc[("2024-06-01", "L6", "EDU5")] # a specific contrat structure at aspecific date
# # str_data_3d.xs("L6", level="Structure") # 
# # str_data_3d.xs("EDU5", level="Contract") # 



#printnable
# Ensure index is proper MultiIndex
# latest_df.index = pd.MultiIndex.from_tuples(latest_df.index, names=["Structure", "Contract"])
# percentile_rank_df.index = pd.MultiIndex.from_tuples(percentile_rank_df.index, names=["Structure", "Contract"])

# # Pivot to 2D
# latest_2d = latest_df["Value"].unstack("Structure")
# percentile_2d = percentile_rank_df["Percentile"].unstack("Structure")

###################################### heatmap values populating #####################################################################
custom_colorscale = [
    [0.0,  'rgb(150, 190, 255)'],  # Strong Light Blue for 0%
    [0.05, 'rgb(170, 205, 255)'],  # Distinctly lighter for 5%
    [0.10, 'rgb(190, 220, 255)'],  # Clearly lighter for 10%
    [0.20, 'rgb(215, 235, 255)'],  # Very light blue for 20%

    # --- Middle Section (Low-distinction area) ---
    # The color changes very little here, as requested.
    [0.5,  'rgb(240, 245, 240)'],  # A neutral, pale green-white for the midpoint

    # --- Green Extreme (High-distinction area) ---
    [0.80, 'rgb(215, 245, 215)'],  # Very light green for 80%
    [0.90, 'rgb(190, 235, 190)'],  # Clearly darker for 90%
    [0.95, 'rgb(170, 225, 170)'],  # Distinctly darker for 95%
    [1.0,  'rgb(150, 215, 150)']   # Strong Light Green for 100%
]

def generate_heatmap(rounding, layer_df):
    # Extract unique orders
    structure_order = layer_df.index.get_level_values('Structure').unique()
    contract_order = layer_df.index.get_level_values('Contract').unique()

    # Convert MultiIndex Series to 2D DataFrame
    df_2d = layer_df.unstack(level=0)['Value'].reindex(index=contract_order, columns=structure_order)

    # Prepare axes and matrix
    x_labels = df_2d.columns.tolist()
    y_labels = df_2d.index[::-1].tolist()  # reverse
    z = df_2d.values[::-1]                 # reverse rows

    # Initialize Heatmap
    fig = go.Figure(go.Heatmap(
        z=z,
        x=x_labels,
        y=y_labels,
        colorscale=custom_colorscale,
        showscale=False
    ))

    # Layout
    fig.update_layout(
        plot_bgcolor='lightgray',
        xaxis=dict(side='top', showgrid=False, fixedrange=True,
                   tickfont=dict(size=14, family="Orbitron", color="black")),
        yaxis=dict(side='top', showgrid=False, fixedrange=True,
                   tickfont=dict(size=14, family="Orbitron", color="black")),
        height=800,
        margin=dict(l=5, r=5, t=5, b=5),
    )

    # Vertical and horizontal lines
    x_lines = [0.5, 3.5, 13.5, 23.5, 27.5]
    y_lines = [4.5, 8.5, 12.5, 16.5, 20.5, 24.5, 28.5]
    y_max = len(y_labels) - 1

    for x in x_lines:
        if x < len(x_labels) - 1:
            fig.add_vline(x=x, line_width=1.5, line_dash="solid", line_color="white")

    for y in y_lines:
        if y < len(y_labels) - 1:
            fig.add_hline(y=y_max - y, line_width=1.5, line_dash="solid", line_color="white")

    # Colored vertical segments
    vline_segments = [
        (-0.5, 3.5, 'grey'), (3.5, 7.5, 'red'), (7.5, 11.5, 'green'),
        (11.5, 15.5, 'blue'), (15.5, 19.5, 'gold'), (19.5, 23.5, 'purple'),
        (23.5, 27.5, 'orange'), (27.5, 31.5, 'pink')
    ]

    for y0, y1, color in vline_segments:
        if y0 > y_max + 0.5:
            break
        yf = min(y1, y_max + 0.5)
        fig.add_shape(
            type='line',
            x0=-0.5, x1=-0.5,
            y0=y_max - y0,
            y1=y_max - yf,
            line=dict(color=color, width=2.5),
            layer='above'
        )

    # Annotation text
    text = [[
        f"{val:.{rounding}f}" if isinstance(val, (int, float)) and not np.isnan(val)
        else ("" if val is None or (isinstance(val, float) and np.isnan(val)) else str(val))
        for val in row
    ]for row in z]

    fig.update_traces(
        text=text,
        texttemplate="%{text}",
        hovertemplate="<b>%{x} | %{y}</b><br>Val: %{z:.1f} <extra></extra>"
    )

    return fig




def create_blank_heatmap(layer_df):
    structure_order = layer_df.index.get_level_values('Structure').unique().tolist()
    contract_order = layer_df.index.get_level_values('Contract').unique().tolist()

    empty_z =  z_empty = np.zeros((len(contract_order ), len(structure_order)))
    text_empty = [["" for _ in structure_order] for _ in contract_order ]

    fig = go.Figure(
        data=go.Heatmap(
        z= empty_z,
        x= structure_order,
        y= contract_order,
        text= text_empty,
        #hoverinfo="text",
        hovertemplate="<b>%{x} | %{y}</b><br>Val: %{z:.1f} <extra></extra>",
        colorscale=[[0, "red"], [1, "green"]],  # Initial dummy
        showscale=False
        )
    )

    fig.update_layout(
        plot_bgcolor='lightgray',
        xaxis=dict(side='top', showgrid=False, tickfont=dict(size=14, family="Orbitron", color="black")),
        yaxis=dict(side='top', showgrid=False, tickfont=dict(size=14, family="Orbitron", color="black")),
        height=800,
        margin=dict(l=5, r=5, t=5, b=5),
    )
    x_coordinate_for_line= {0.5, 3.5, 13.5, 23.5, 27.5}
    for x_line in x_coordinate_for_line:
        if x_line < len(structure_order)-1:
            fig.add_vline(
                x=x_line,
                line_width=1,
                line_dash="solid",
                line_color="white",
                # annotation_text="Key Event", # Optional: add a label to the line
                # annotation_position="top right"
            )

    y_coordinate_for_line= {4.5, 8.5, 12.5, 16.5, 20.5, 24.5, 28.5}
    for y_line in y_coordinate_for_line:
         if y_line < len(contract_order)-1:
            fig.add_hline(
                y= len(contract_order)-y_line,
                line_width=1,
                line_dash="solid",
                line_color="white",
                # annotation_text="Key Event", # Optional: add a label to the line
                # annotation_position="top right"
            )
    return fig


################# heatmap coloring  ##############################################################
def color_heatmap(fig, type, layer_df): #initial value populating
    try:
        if not isinstance(layer_df.index, pd.MultiIndex):
            raise ValueError("Input 'fig' must be a Figure with a Heatmap trace at index 0.")
        structure_order = layer_df.index.get_level_values('Structure').unique().tolist()
        contract_order = layer_df.index.get_level_values('Contract').unique().tolist()

        # 2. Convert MultiIndex Series to 2D DataFrame
        df_2d = layer_df.unstack(level=0)['Value']
        df_2d = df_2d.reindex(index=contract_order, columns=structure_order)
        new_z = df_2d.values[::-1]                        # Matrix (rows reversed)

        # 4. Update existing heatmap trace (assumes 1 trace only)
        if fig.data and isinstance(fig.data[0], go.Heatmap):
            fig.data[0].z = new_z  # this controls coloring
            fig.data[0].colorscale = custom_colorscale
            fig.data[0].showscale = False
            fig.data[0].hoverinfo = 'skip'
        ###If you want to style cells (e.g. bold outline or highlight based on a condition), you’ll need to use go.Heatmap + shapes or overlay a Scatter trace
        return fig
    
    # --- Specific Error Handling ---
    except (ValueError, TypeError) as e:
        print(f"Input Validation Error in  color_heatmap:  {e}")
        return fig # Return the original figure
    except KeyError as e:
        print(f"Data Structure Error in color_heatmap: Missing expected level or column: {e}")
        return fig
    # --- General Fallback Error Handling ---
    except Exception as e:
        print(f"An unexpected error in color_heatmap occurred: {e}")
        return fig
    


########################## highlighter filter ####################

def filter_grey (fig, type, layer_df): #initial value populating
    try:
        if not isinstance(layer_df.index, pd.MultiIndex):
            raise ValueError("Input 'fig' must be a Figure with a Heatmap trace at index 0.")
        structure_order = layer_df.index.get_level_values('Structure').unique().tolist()
        contract_order = layer_df.index.get_level_values('Contract').unique().tolist()

        # 2. Convert MultiIndex Series to 2D DataFrame
        df_2d = layer_df.unstack(level=0)['Value']
        df_2d = df_2d.reindex(index=contract_order, columns=structure_order)
        new_z = df_2d.values[::-1]                        # Matrix (rows reversed)

        # Create mask for the condition
        """" Set gray values for cells not meeting condition
        Using None for values that don't meet the condition will make them transparent,
        allowing a background color or another trace to show through if desired.
        If a specific gray color is needed, you would assign a numerical value and
        define that value in your colorscale to map to gray """

        if(type== 595):
            mask = (new_z >= 95) | (new_z <= 5)
        elif(type== 1090):
            mask = (new_z >= 90) | (new_z <= 10)

        colored_z = np.where(mask, new_z, None)
        # 4. Update existing heatmap trace (assumes 1 trace only)
        if fig.data and isinstance(fig.data[0], go.Heatmap):
            fig.data[0].z = colored_z  # this controls coloring
            fig.data[0].showscale = False
            fig.data[0].hoverinfo = 'skip'
        ###If you want to style cells (e.g. bold outline or highlight based on a condition), you’ll need to use go.Heatmap + shapes or overlay a Scatter trace
        return fig

    # --- Specific Error Handling ---
    except (ValueError, TypeError) as e:
        print(f"Input Validation Error in filter_grey : {e}")
        return fig # Return the original figure
    except KeyError as e:
        print(f"Data Structure Error: Missing expected level or column in filter_grey : {e}")
        return fig
    # --- General Fallback Error Handling ---
    except Exception as e:
        print(f"An unexpected error occurred in filter_grey: {e}")
        return fig






######################################################## hover t3mplate ##########################3

def hovertemplate_heatmap(heatmap, latest_df, roll_down_df, roll_up_df, percentile_df):
    try:
        if not isinstance(latest_df.index, pd.MultiIndex):
            raise ValueError("Input 'fig' must be a Figure with a Heatmap trace at index 0.")
        structure_order = latest_df.index.get_level_values('Structure').unique().tolist()
        contract_order = latest_df.index.get_level_values('Contract').unique().tolist()
        x_labels = structure_order
        y_labels = contract_order[::-1]

        # 2. Convert MultiIndex Series to 2D DataFrame
        processed_dfs = {}
        source_data_map = {
            'Latest': latest_df,
            'rank': percentile_df,
            'RlDn': roll_down_df,
            'RlUp': roll_up_df,
        }
        for name, df_series in source_data_map.items():
            if isinstance(df_series, pd.DataFrame):
                # If it's a DataFrame with a 'Value' column, select it first.
                df_series = df_series['Value']
            # Unstack the 'Structure' level to become the columns.
            df_2d = df_series.unstack(level='Structure')
            df_2d = df_2d.reindex(index=contract_order, columns=structure_order)
            processed_dfs[name] = df_2d

        # hovertext ##
        hover_text_matrix = []
        for contract in y_labels:
            row_texts = []
            for structure in x_labels:
                cell_info = []
                for name, df in processed_dfs.items():
                    value = df.loc[contract, structure]
                    if pd.notna(value) and value != "":
                        try:
                            cell_info.append(f"{name}: {float(value):.1f}")
                        except (ValueError, TypeError):
                            cell_info.append(f"{name}: {value}")  

                # Join all factors with an HTML line break
                row_texts.append("<br>".join(cell_info))
            hover_text_matrix.append(row_texts)

        # Reconstruct the Figure object from the dictionary
        heatmap = go.Figure(heatmap)
        heatmap.update_traces(
            selector=dict(type="heatmap"),  # Optional if only one trace
            customdata= hover_text_matrix,
            hovertemplate="<b>%{x} | %{y}</b><br>%{customdata}<extra></extra>"
        )
        return heatmap
    
     # --- Specific Error Handling ---
    except (ValueError, TypeError) as e:
        print(f"Input Validation Error in hovertemplate_heatmap: {e}")
        return heatmap # Return the original figure
    except KeyError as e:
        print(f"Data Structure Error: Missing expected level or column in hovertemplate_heatmap: {e}")
        return heatmap
    # --- General Fallback Error Handling ---
    except Exception as e:
        print(f"An unexpected error occurred  in hovertemplate_heatmap: {e}")
        return heatmap

###################################################### side panel #############################
def get_adjacent_values(str_data_3d,  x_val, y_val): #D3, SFR3
    latest_date = str_data_3d.index.get_level_values("Date").unique()[0]
    latest_df = str_data_3d.loc[latest_date]
    structure_order = latest_df.index.get_level_values('Structure').unique().tolist()
    contract_order = latest_df.index.get_level_values('Contract').unique().tolist()

    df_series = latest_df['Value']
    df_2d = df_series.unstack(level='Structure')
    df_2d = df_2d.reindex(index=contract_order, columns=structure_order)
    
    x_labels = df_2d.columns.tolist()  # S3, l3, L6   
    y_labels = df_2d.index.tolist() # SFR1,SFR2...
    
    try:
        curr_col = x_labels.index(x_val)
        curr_row= y_labels.index(y_val)
        
    except ValueError:
        return None, None
    prev_data, next_data = None, None # we need value in the same column
    if curr_row > 0:
        prev_data = df_2d.iloc[curr_row- 1 , curr_col]
    if curr_row < len(y_labels) - 1:
        next_data = df_2d.iloc[curr_row+ 1,  curr_col]
    # print("cc", curr_col, "cr", curr_row)
    # print("pv", prev_data,"nv", next_data)
    return prev_data, next_data 



def generate_heatmap_detail_panel (clicked_series, x_val, y_val, prev_val, next_val):
    clicked_series = pd.Series(clicked_series.iloc[:, 0].values)
    #print(type(clicked_series), len(clicked_series))
    series= process_series(clicked_series, window=11, k=2)
    reversed_series= series[::-1]
    # --- Step 1: Create the Sparkline Plot ---
    sparkline_fig = go.Figure(
        go.Scatter(
            x= reversed_series.index,
            y= reversed_series,
            mode='lines',
            #line_shape='spline',
            line_shape='linear',
            line=dict(width=2, color='#0d6efd'),
            #fill='tozeroy', 
            fillcolor='rgba(13, 110, 253, 0.2)'
        )
    )
    sparkline_fig.update_layout(
        template='plotly_white',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=4, b=4),
        height=60,
        xaxis=dict(showgrid=False, showticklabels=False, type='category'),
        yaxis=dict(showline=True, linecolor='gray',showgrid=False, ticks='outside',tickfont=dict(size=8) ),
        #showgrid=True, gridcolor='lightgray', gridwidth=0.5,layer='below traces', showticklabels=False
    )

    #step 2   Mini Bar Chart: Volatility or Daily Delta View
    #print(reversed_series, reversed_series.diff())
    barchart_cod_fig = go.Figure(
        go.Bar(
            x=reversed_series.index,
            y=reversed_series.diff(),
            marker_color=['#28a745' if x > 0 else '#dc3545' for x in reversed_series.diff()],
            width=0.8,
        )
    )
    
    barchart_cod_fig.update_layout(
        template='plotly_white',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=4, b=4),
        height=60,
        xaxis=dict(showgrid=False, showticklabels=False, type='category'),
        yaxis=dict(showgrid=False, showticklabels=False),
    )

    #other matrics step3 
    latest_val= series.iloc[0]
    rank= get_rank(series, latest_val)
    min_val= series.min()
    max_val= series.max() 
    roll_down_val=  prev_val-latest_val if prev_val is not None else None
    if(roll_down_val is not None):
        rd= f"▼{abs(roll_down_val):.1f}" if roll_down_val < 0 else f"▲{abs(roll_down_val):.1f}" if roll_down_val > 0 else ''
    roll_up_val=  next_val-latest_val if next_val is not None else None
    if(roll_up_val is not None):
        ru= f"▼{abs(roll_up_val):.1f}" if roll_up_val < 0 else f"▲{abs(roll_up_val):.1f}" if roll_up_val > 0 else ''
    
    # Determine if it's a peak or a valley in the forward curve
    if pd.isna(roll_down_val) or pd.isna(roll_up_val):
        risk_reward_diff_val = None
        risk_reward_ratio_val = None
        arrow= ''
    else:
        abs_rd = abs(roll_down_val)
        abs_ru = abs(roll_up_val)
        # Determine if it's a peak or a valley in the forward curve
        is_valley = (roll_down_val > 0 and roll_up_val >= 0)
        is_peak = (roll_down_val < 0 and roll_up_val <= 0)
        # Case 1: Peak or Valley
        if is_valley:
            risk_reward_diff_val = min(abs_rd, abs_ru)
            risk_reward_ratio_val = 99
            arrow = '⬆'
        elif is_peak:
            risk_reward_diff_val = min(abs_rd, abs_ru)
            risk_reward_ratio_val = 99
            arrow = '⬇'
        else:
            # Avoid division by zero
            if abs_rd > abs_ru:
                    arrow = '⬇' if roll_down_val < 0 else '⬆'
            else:
                arrow = '⬇' if roll_up_val < 0 else '⬆'
            risk_reward_diff_val = abs(abs_rd - abs_ru)
            
            if (abs_rd== 0) & (abs_ru== 0):
                risk_reward_ratio_val = 0
            elif (abs_rd == 0) | (abs_ru == 0):
                risk_reward_ratio_val = 99 if abs_ru+abs_ru > 0 else -99
            else:
                risk_reward_ratio_val = min(99, max(abs_rd, abs_ru) / min(abs_rd, abs_ru))
                

    if risk_reward_ratio_val is not None:
        risk_reward_ratio = f"{arrow}{risk_reward_ratio_val:.1f}"
    else:
        risk_reward_ratio = None
    if risk_reward_diff_val is not None:
        risk_reward_diff = f"{arrow}{risk_reward_diff_val:.1f}"
    else:
        risk_reward_diff = None     


    std_dev= series.std()
    mean = series.mean()
    median = series.median() 
    range_span = max_val - min_val
    z_score = (latest_val - mean) / std_dev if std_dev != 0 else np.nan

     # --- Step 4: Assemble the Panel's Layout Components ---
    panel_content = dbc.Container([
        # Header Row with Title and Close Button
        dbc.Row([
            dbc.Col(html.H5(f"{x_val} | {y_val}", className="my-auto"), width='auto'),
            dbc.Col(
                html.Span(
                    "×",  # The 'x' character for the button
                    id="details-panel-close-btn",
                    n_clicks=0,
                    className="panel-close-button",  # Custom class for your separate CSS file
                    style={'cursor': 'pointer', 'fontSize': '36px', 'font-weight': 'bold', 'lineHeight': '1'}      # Changes the mouse cursor to a pointer on hover
                ),
            width="auto",
            )
        ], align="center", justify="between", className="mb-3"),

        # Main Value Display and Sparkline
        dbc.Card(dbc.CardBody([
            html.H6("Current Price", className="card-subtitle mb-2 text-muted"),
            html.H3(f"{latest_val:.2f}" if latest_val is not None else "N/A", className="card-title"),
            dcc.Graph(figure=sparkline_fig, config={'displayModeBar': False}, className="mt-2")
        ])),

        # Daily Change Bar Chart
        dbc.Card(dbc.CardBody([
            html.H6("Daily Change", className="card-subtitle mb-2 text-muted"),
            dcc.Graph(figure=barchart_cod_fig, config={'displayModeBar': False})
        ]), className="mt-3"),
        
        # Key Metrics Grid
        html.H6("Statistical Analysis", className="mt-4 mb-2"),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.P("Rank", className="text-muted small mb-0"),
                html.H5(f"{rank:.0f}%" if rank is not None else "N/A")
            ])), width=6),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.P("Z-Score", className="text-muted small mb-0"),
                html.H5(f"{z_score:.2f}" if z_score is not None else "N/A")
            ])), width=6),
        ], className="g-2"),

        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Min", className="text-muted small mb-0"),
            html.H5(f"{min_val:.1f}" if min_val is not None else "N/A")
        ])), width=6),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.P("Max", className="text-muted small mb-0"),
                html.H5(f'{max_val:.1f}' if max_val is not None else "N/A")
            ])), width=6),
        ], className="g-2 mt-2"),

        dbc.Row([
             dbc.Col(dbc.Card(dbc.CardBody([
                html.P("Roll Dn", className="text-muted small mb-0"),
                html.H5(f"{rd}" if roll_down_val is not None else "N/A")
            ])), width=6),
            
            dbc.Col(dbc.Card(dbc.CardBody([
                html.P("Roll Up", className="text-muted small mb-0"),
                html.H5(f"{ru}" if roll_up_val is not None else "N/A")
            ])), width=6),
        ], className="g-2 mt-2"),

     

        # Roll and Risk/Reward Analysis
        html.H6("Roll & Risk Analysis", className="mt-4 mb-2"), 
        dbc.ListGroup([
            # dbc.ListGroupItem([html.Span("Roll Down", className="fw"), html.Span(f"{roll_down:.1f}" if roll_down is not None else "N/A", className="float-end")]),
            dbc.ListGroupItem([html.Span("Std Dev", className="fw"), html.Span(f"{std_dev:.1f}" if std_dev is not None else "N/A", className="float-end")]),
            dbc.ListGroupItem([html.Span("Median", className="fw"), html.Span(f"{median:.1f}" if median is not None else "N/A", className="float-end")]),
            dbc.ListGroupItem([html.Span("Mean", className="fw"), html.Span(f"{mean:.1f}" if mean is not None else "N/A", className="float-end")]),
            dbc.ListGroupItem([html.Span("Risk/Reward Diff", className="fw"), html.Span(f"{risk_reward_diff}" if risk_reward_diff is not None else "N/A", className="float-end")]),
            dbc.ListGroupItem([html.Span("Risk/Reward Ratio", className="fw"), html.Span(f"{risk_reward_ratio}" if risk_reward_ratio is not None else "N/A", className="float-end")]),
            dbc.ListGroupItem([html.Span("Range Span", className="fw"), html.Span(f"{range_span:.1f}" if range_span is not None else "N/A", className="float-end")]),
            # dbc.ListGroupItem([html.Span("Max Value", className="fw"), html.Span(f"{max_val:.2f}" if max_val is not None else "N/A", className="float-end")]),
            # dbc.ListGroupItem([html.Span("Min Value", className="fw"), html.Span(f"{min_val:.2f}" if min_val is not None else "N/A", className="float-end")]),
            
        ], flush=True),

    ], fluid=True, style={'padding': '1rem'})
    
    return panel_content



    

