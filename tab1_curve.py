from dash import dcc, html
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import logging
from datetime import datetime
import pymannkendall as mk
from scipy.stats import linregress

from str_cal import get_ratio, rolling_bounds_filter


def create_tab1_view():
    view= dcc.Tab(label='Curve View', value='tab1',
            style={"height": "42px","borderRadius": "8px 8px 0 0","padding": "8px 16px","marginRight": "4px","backgroundColor": "#2b2e35","color":  "#c0c4cc","fontWeight": "500","border": "1px solid #3a3f4b","borderBottom": "none","transition": "background-color 0.3s, color 0.3s"
            },
            selected_style={"height": "45px","borderRadius": "8px 8px 0 0","padding": "8px 16px","backgroundColor": "#1f2128","color": "#ffffff","fontWeight": "600","border": "1px solid #5e636e","borderBottom": "none","boxShadow": "0px -2px 6px rgba(0, 0, 0, 0.4)"
            },
            children=[
                dbc.Row([
                    dbc.Col(dcc.Loading(
                        id="loading-curve",
                        type="circle",
                        children=html.Div(dcc.Graph(id='curve-plot', config={'scrollZoom': True, 'displayModeBar': False}),className="border p-1 my-2 rounded")
                        ), width=10
                    ),
                    dbc.Col([
                        html.Div([
                            html.H5(
                                "Plot Controls",
                                style={
                                    "color": "#c0c4cc", "textAlign": "center", "padding": "8px 16px",
                                    "backgroundColor": "#2b2e35", "fontWeight": "500", "fontSize": "16px",
                                    "borderBottom": "1px solid #3a3f4b", "margin": "0"
                                }
                            ),

                            dbc.Checklist(
                                id='plot-flags',
                                options=[
                                    {"label": "Latest", "value": "Latest"},
                                    {"label": "Settle", "value": "Settle"},
                                    {"label": "Date1", "value": "Date1"},
                                    {"label": "Date2", "value": "Date2"},
                                    {"label": "MA", "value": "MA"},
                                    {"label": "Median", "value": "MED"},
                                    {"label": "Quantile Series", "value": "quant_ser"},
                                    {"label": "Bollinger Band", "value": "BB"},
                                    {"label": "XN", "value": "XN"}
                                ],
                                value=["Latest", "Settle", "XN"],
                                switch=True,
                                className="control-panel-1"
                            ),

                            dbc.Stack([
                                dbc.Row([
                                    dbc.Col(dbc.Label("Local win"), width=6),
                                    dbc.Col(dbc.Input(id="win-local", type="number", value=21, min=1, step=1, debounce=True), width=6)
                                ], id="win-local-row", className="mb-2", style={"display": "none"}),

                                dbc.Row([
                                    dbc.Col(dbc.Label("Settle offset"), width=6),
                                    dbc.Col(dbc.Input(id="Settle_days-input", type="number", value=1, min=1, step=1, debounce=True), width=6)
                                ], id="settle-row", className="mb-2", style={"display": "none"}),

                                dbc.Row([
                                    dbc.Col(dbc.Label("Date 1"), width=4),
                                    dbc.Col(dbc.Input(id="date1-input", type="date", value="2025-06-05"), width=8)
                                ], id="date1-row", className="mb-2", style={"display": "none"}),

                                dbc.Row([
                                    dbc.Col(dbc.Label("Date 2"), width=4),
                                    dbc.Col(dbc.Input(id="date2-input", type="date", value="2024-09-25"), width=8)
                                ], id="date2-row", className="mb-2", style={"display": "none"}),

                                dbc.Row([
                                    dbc.Col(dbc.Label("Quantile"), width=6),
                                    dbc.Col(dbc.Input(id="quantile-input", type="number", value=95, min=0, max=100, step=1, debounce=True), width=6)
                                ], id="quantile-row", className="mb-2", style={"display": "none"}),

                                dbc.Row([
                                    dbc.Col(dbc.Label("BB Std Dev"), width=6),
                                    dbc.Col(dbc.Input(id="bb-std-input", type="number", value=1, min=1, step=1, debounce=True), width=6)
                                ], id="bb-std-row", className="mb-2", style={"display": "none"}),

                            ], gap=1)
                        ],

                        style={
                            "border": "1px solid #3a3f4b",
                            "borderRadius": "8px",
                            "backgroundColor": "#2b2e35",
                            "padding": "10px",
                            "marginTop": "5px"
                        })
                    ], width=2, style={"paddingLeft": "0px", "marginTop": "2px"})
                ]),
            #]),
                # --- NEW ROW 2: SORTABLE TABLE ---  ###### table ############################################
                dbc.Row([
                    dbc.Col(dcc.Loading(
                        id="loading-table",
                        type="circle",
                        children=html.Div(  # <-- Wrap AgGrid
                            dag.AgGrid(
                                id='contracts-table',
                                className="ag-theme-alpine-dark top-scroll",
                                columnDefs=[],            # set columns later
                                rowData=[],               # will be provided by callback
                                defaultColDef={"sortable": True, "resizable": True, "filter": True},
                                columnSize="autoSize", # "sizeToFit", "autoSize", "responsiveSizeToFit", 
                                dashGridOptions={"pagination": False, "domLayout": "autoHeight" },  # 👈 makes grid height fit content
                                enableEnterpriseModules=True,#sparline
                                style={"width": "100%"},  # or use a maxHeight with scroll
                                
                            ),
                        style={"overflow": "hidden", "position": "relative"}  # container style
                        )
                    ), width=12)
                ], className="my-2"), # Add some margin 
            ])
    return view
    


def init_plot(title):
    """
    Initialize Plotly figure with standardized layout.
    """
    fig = go.Figure()
    fig.update_layout(

        title=dict(text=title, x=0.5, y=0.99, xanchor="center", font=dict(size=14,  color= "#1f2128")),
        #template="plotly_dark", #"plotly" Default white background
        hovermode="x unified",
        legend=dict(
            x=0.5, y=0.95,
            orientation="h",
            xanchor="center",
            yanchor="bottom"
        ),
        height=470,
        margin=dict(l=10, r=10, t=30, b=20),
        dragmode="pan"
    )
    return fig


def add_plot_study(fig, name, item, base_label=None, color=None, show_values=0):
    """
    Add a study (line or band) to a Plotly figure.
    """
    if isinstance(item, pd.Series):
        item = {
            "type": "line",
            "data": item,
            "label": name,
            "color": color,
            "dash": "solid"
        }

    if not isinstance(item, dict):
        return fig

    label = base_label or name or item.get("label")
    if item.get("type") == "line":
        series = item.get("data")
        if isinstance(series, pd.Series):
            fig = add_series(fig, data=series, name=label,color=item.get("color", color),dash=item.get("dash", "dot"),opacity=item.get("opacity", 1.0),hovertemplate=item.get("hovertemplate","%{y:.2f} @%{fullData.name}<extra></extra>"), show_values= show_values)
    elif item.get("type") == "band":
        band = item.get("data", {})
        fig = add_band(fig, upper=band.get("upper"), lower=band.get("lower"),name=label, color=item.get("color", "rgba(180,180,250,0.3)"), zorder=0)
    return fig


def add_band(fig, upper, lower, name, color="rgba(180,180,250,0.3)", zorder=1):
    """
    Add shaded band (e.g., Bollinger Bands) to the plot.
    """
    if upper is None or lower is None:
        return fig

    fig.add_trace(go.Scatter(
        x=lower.index,
        y=lower.values,
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip',
        name=f"{name} Lower"
    ))

    fig.add_trace(go.Scatter(
        x=upper.index,
        y=upper.values,
        mode="lines",
        line=dict(width=0),
        fill='tonexty',
        fillcolor=color,
        name=name,
        customdata=lower.values,
        hovertemplate="(%{customdata:.2f}, %{y:.2f}) @%{fullData.name}<extra></extra>"
    ))
    return fig

def curve_at_datex(out_ser,comdty, str_name, curve_len, DEFAULT_WINDOW, DEFAULT_OUTLIER_K):
    if out_ser is None or str_name is None:
        return {}
    ratio= get_ratio(str_name)
    max_col= len(out_ser) #35  i.e. 
    try:
        curve_len = int(curve_len)
    except ValueError:
        curve_len= min(20, max_col- len(ratio)+1)
    
    if curve_len <= 0:
        return {}
    
    if comdty == "SZI0":
        str_curve = (out_ser.rolling(window=len(ratio), min_periods=len(ratio)).apply(lambda x: np.dot(x, ratio), raw=True))
    elif str_name == "Out" and comdty in ["meets", "SZI0"]:
        default_ratio = pd.Series([1.0], index=[0], name="Out")
        str_curve = (out_ser.rolling(window=len(default_ratio), min_periods=len(default_ratio)).apply(lambda x: np.dot(x, default_ratio), raw=True))
        str_curve = rolling_bounds_filter(str_curve, window=DEFAULT_WINDOW, k=DEFAULT_OUTLIER_K)
    else:
        str_curve = str_curve = (out_ser.rolling(window=len(ratio), min_periods=len(ratio)).apply(lambda x: np.dot(x, ratio), raw=True))
        str_curve= str_curve*100
        str_curve = rolling_bounds_filter(str_curve, window=DEFAULT_WINDOW, k=DEFAULT_OUTLIER_K)
    str_curve =  str_curve.shift(-(len(ratio)-1))
    return str_curve[:curve_len]


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


def add_series(fig, data, name, color=None, mode="lines+markers", dash=None, opacity=1.0,
                hovertemplate="%{y:.2f} @%{fullData.name}<extra></extra>", show_values= 0):
    """
    Add line or marker trace to Plotly figure.
    """
    # Initialize a dictionary for additional parameters
    kwargs = {}
    if show_values:
        mode += "+text" # Add "text" to the mode to display values
        kwargs['text'] = [f'{val:.1f}' for val in data.values]
        kwargs['textposition'] = "top center"
        text_colors = ['red' if val < 0 else 'black' for val in data.values]
        #kwargs['textposition'] = ["top center" if val >= 0 else "bottom center" for val in data.values]
        kwargs['textfont'] = dict(color=text_colors)
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data.values,
        mode=mode,
        name=name,
        line=dict(color=color, dash='solid'),
        opacity=opacity,
        hovertemplate=hovertemplate,
        **kwargs  # Unpack the dictionary to add the conditional parameters
    ))
    return fig



def add_arrows(fig, data, name=None):
    if len(data) < 3:
        print("Not enough data points to apply the full arrow logic.")
        return fig
        
    arrow_x = []
    arrow_y = []
    arrow_symbols = []
    arrow_colors = []
    hover_texts = []

    # Iterate through all points to assign a signal to each one
    offset_amount = 1 
    adjusted_arrow_y = [] # This list will store the final, offset y-values
    for i in range(len(data)):
        if i == 0 or i == len(data) - 1:
            symbol = "circle"
            color = "gray"
            hover_text = "edge"

        current_val = data.iloc[i]
        
        # Default to neutral for edge cases
        symbol = "circle"
        color = "grey"
        
        # Check for non-edge points
        if i > 0 and i < len(data) - 1:
            prev_val = data.iloc[i-1]
            next_val = data.iloc[i+1]

            # 1. Peak/Bottom Override Logic
            if current_val > prev_val and current_val > next_val:
                symbol = "arrow-down"
                color = "red"
                hover_text = "Peak"
            elif current_val < prev_val and current_val < next_val:
                symbol = "arrow-up"
                color = "green"
                hover_text = "Bottom"
            
            # 2. "Farthest Value" Logic (if not a peak or bottom)
            else:
                lower_adj = min(prev_val, next_val)
                higher_adj = max(prev_val, next_val)
                
                dist_to_lower = abs(current_val - lower_adj)
                dist_to_higher = abs(current_val - higher_adj)
                
                if dist_to_lower > dist_to_higher:
                    symbol = "arrow-down"
                    color = "red"
                    hover_text = "Good for Short"
                elif dist_to_higher > dist_to_lower:
                    symbol = "arrow-up"
                    color = "green"
                    hover_text = "Good for Long"
                else: # Equal distance
                    symbol = "circle"
                    color = "gray"
                    hover_text = "Neutral"

        # --- NEW: Adjust Y-Value based on the symbol we just found ---
        final_y = current_val # Default to the original value
        if "down" in symbol:
            final_y = current_val + offset_amount # Move UP
        elif "up" in symbol:
            final_y = current_val - offset_amount # Move DOWN

        arrow_x.append(data.index[i])
        adjusted_arrow_y.append(final_y)
        arrow_symbols.append(symbol)
        arrow_colors.append(color)
        hover_texts.append(hover_text)

    fig.add_trace(go.Scatter(
        x=arrow_x,
        y=adjusted_arrow_y,
        mode='markers',
        #name="Trading Signals",
        hoverinfo='text',
        hovertext=hover_texts,
        showlegend=False,
        opacity=0.2,
        marker=dict(
            symbol=arrow_symbols,
            color=arrow_colors,
            size=12
        )
    ))
    return fig

def generate_curve_plot(str_df: pd.DataFrame, raw_df: pd.DataFrame ,plot_flags: dict,comdty:str= "SR3",curve_len:int=20, str_name :str= "L6",Settle: int = None,date1=None,date2=None,win_local: int = 21,quantile: float = None,bb_std: float = None, DEFAULT_WINDOW=21, DEFAULT_OUTLIER_K=2):
    if str_df is None or str_df.empty:
        return warning_plot_copy2("⚠ No data to plot")

    fig = init_plot(f"{comdty}{str_name}")
    #print(str_df.head())
    # ---------- Safe helpers ----------
    def safe_parse_date(x):
        """Convert string to datetime if possible, else pass-through."""
        if x is None:
            return None
        if isinstance(x, str):
            try:
                return datetime.strptime(x, "%Y-%m-%d")
            except ValueError:
                logging.warning(f"Invalid date string passed: {x}")
                return None
        return pd.to_datetime(x, errors="coerce", format='mixed')

    def snap_to_index(dt):
        """Snap a datetime to nearest valid index value if not present."""
        if dt is None:
            return None
        if dt not in raw_df.index:
            try:
                sorted_idx = raw_df.index.sort_values()
                #print(sorted_idx[:-100])
                nearest_idx = sorted_idx.get_indexer([dt], method="nearest")[0]
                snapped = sorted_idx[nearest_idx]
                logging.warning(f"{dt} not in index, snapped to {snapped}")
                return snapped
            except Exception:
                return None
        return dt

    def safe_study(name, func, *args, **kwargs):
        """Run study with guard, add to fig if successful."""
        try:
            study = func(*args, **kwargs)
            #print(name, func, study)
            if study is not None and (not hasattr(study, "empty") or not study.empty):
                return add_plot_study(fig, name, study, show_values=0)
        except Exception as e:
            logging.warning(f"Skipping study '{name}': {e}", exc_info=True)
        return fig

    # ---------- Dates ----------
    date1 = snap_to_index(safe_parse_date(date1))
    date2 = snap_to_index(safe_parse_date(date2))
    # ---------- Plotting flags ----------
    #curve_at_datex(out_ser,comdty, str_name, curve_len, DEFAULT_WINDOW, DEFAULT_OUTLIER_K)
    if plot_flags.get("Settle") and Settle is not None:
        try:
            Settle= int(Settle)
            Settle = max(-len(str_df), min(Settle, len(str_df) - 1))
            Settle = max(-win_local, min(Settle, win_local - 1))
            out_ser = raw_df.iloc[Settle] if raw_df.shape[0] > Settle else None
            settle_row = curve_at_datex(out_ser, comdty, str_name, curve_len,DEFAULT_WINDOW, DEFAULT_OUTLIER_K)
            fig = add_plot_study(fig, name=f"Settle(-{Settle})",item={"type": "line", "data": settle_row, "color": "gold"},show_values=0)
        except Exception as e:
            logging.warning(f"Skipping Settle: {e}")

    if plot_flags.get("Date1") and date1 is not None:
        leg = date1.strftime("%Y-%m-%d")
        date_curve= curve_at_datex(raw_df.loc[date1], comdty, str_name, curve_len, DEFAULT_WINDOW, DEFAULT_OUTLIER_K)
        fig = add_plot_study(fig, leg,{"type": "line", "data": date_curve, "color": "darkgreen"},show_values=0)

    if plot_flags.get("Date2") and date2 is not None:
        leg = date2.strftime("%Y-%m-%d")
        date_curve= curve_at_datex(raw_df.loc[date2], comdty, str_name, curve_len, DEFAULT_WINDOW, DEFAULT_OUTLIER_K)
        fig = add_plot_study(fig, leg,{"type": "line", "data": date_curve, "color": "#3a3a3a"},show_values=0)

    # ---------- Studies ----------
    if plot_flags.get("MA"):
        fig = safe_study(f"ma({win_local})", moving_average, str_df, win_local)

    if plot_flags.get("MED"):
        fig = safe_study(f"med({win_local})", median_series, str_df, win_local)

    if plot_flags.get("quant_ser") and quantile is not None:
        fig = safe_study(f"quantile({round(quantile)}%|{win_local})",rolling_quantile_series, str_df, win_local, quantile)

    if plot_flags.get("BB") and bb_std is not None:
        fig = safe_study(f"bb({win_local}|{bb_std})", bollinger_bands, str_df, win_local, bb_std)

    if plot_flags.get("XN"):
        fig = safe_study(f"xn({win_local})", maxmin_band, str_df, win_local)

    # ---------- Latest ----------
    if plot_flags.get("Latest"):
        try:
            latest_row = str_df.iloc[0]
            fig = add_plot_study(fig, "Latest",{"type": "line", "data": latest_row, "color": "blue"},show_values=1)
            fig=  add_arrows(fig, latest_row)
        except Exception as e:
            logging.warning(f"Skipping Latest: {e}")

    # ---------- Final Layout ----------
    #fig.update_layout(title=plot_title, template="plotly_dark")
    return fig

def table_populating_1_2(df, change_period, curve_len_final, str_name):

    df = df.iloc[:min(change_period, df.shape[0]), :min(curve_len_final, df.shape[1])]
    
    ## roll down and roll up and risk rewardd
    first_row = df.iloc[0]
    # contracts = first_row.index 
    roll_down = first_row- first_row.shift(+1) 
    roll_up   = first_row- first_row.shift(-1) 
    # Create dictionaries to quickly map contracts to the calculated values
    roll_down_map = roll_down.to_dict()
    roll_up_map = roll_up.to_dict()
    
    table_data = []
    for contract in df.columns:
        try:
            series = df[contract].dropna()
            if len(series) < 2:
                continue

            latest_price = float(series.iloc[0]) #column2 
            last_settle = float(series.iloc[1]) #column3
            CoD= latest_price- last_settle

            # #column4 Safe % change, clamped between -99% and +99%
            pct_change = (((latest_price - last_settle) / last_settle * 100) if last_settle != 0 else 0)
            pct_change = max(-99, min(pct_change, 99))

            ##column5 sprak line
            reversed_ser= series[::-1]
            SparkLine = reversed_ser.tolist()

            #histogram
            daily_changes= reversed_ser.diff().dropna().tolist()

            #Percentile_rank
            percentile_rank= (series <= latest_price).mean() * 100
            #Std Dev
            std_dev= series.std()
            #mean
            meanv= series.mean()
            #Z-Score
            z_score= (latest_price - meanv) / std_dev if std_dev != 0 else 0
            z_score = max(-99, min(z_score, 99))
            #Minimum / Maximum / Median
            maxv= series.max()
            minv= series.min()
            rangev= maxv- minv
            med= series.median()

            #peaks | valley | support | resistance
            n = max(2, min(len(series) // 5, 10))  # Define window size (n points before and after) to compute peaks or valleys
            peaks_n_valleys = ['-'] * len(series) # Initialize flags

            # Loop through series
            for i in range(n, len(series)-n):
                window = series[i-n:i+n+1]
                if series.iloc[i] == window.max():
                    peaks_n_valleys[i] = "Peak"
                if series.iloc[i] == window.min():
                    peaks_n_valleys[i] = "Valley"

            # Get price levels for peaks and valleys directly
            peak_levels = series.iloc[[i for i, val in enumerate(peaks_n_valleys) if val == "Peak"]]
            valley_levels = series.iloc[[i for i, val in enumerate(peaks_n_valleys) if val == "Valley"]]
            tolerance = 0.5  # for resistance 
            flag = (# Check if latest price is near valley or peak or any resistance or any support
                "Peak" if maxv- latest_price <= tolerance
                else "Valley" if minv- latest_price >= -tolerance
                else "Resistance" if any(abs(latest_price - lvl) <= tolerance for lvl in peak_levels)
                else "Support" if any(abs(latest_price - lvl) <= tolerance for lvl in valley_levels)
                else "-"
            )

            # trend and strength of trend by mann- kendel and R square 
            """
            S: The core of the test is the calculation of the statistic S. For a time series x1,x2,…,xn (where n=21 in your case), S is calculated by comparing every possible pair of data points (xj,xi) 
            where j>i. The formula is:
                S= (i=1)∑(n−1)  (j=i+1)∑(n) sgn(xj−xi)
            A positive value of S indicates a tendency for the series to increase over time, and a negative value indicates a tendency to decrease.
            The magnitude of S reflects the strength of the trend's monotonic nature.
            P-value: The significance of the trend is determined by the p-value. For n≥10, the statistic S can be approximated by a normal distribution with a mean of 0.
            The p-value is the probability of observing a value of S as extreme as, or more extreme than, the one calculated from your data, assuming there is no trend (the null hypothesis).
            A low p-value (typically < 0.05) leads to the rejection of the null hypothesis, confirming a statistically significant trend.

            R2 measures how well the linear model fits the data. 
            
            If Mann-Kendall p-value ≤ 0.05:
                If linear regression slope > 0 (upward trend):
                    If R-squared > 0.7: "↑↑" (Strong Upward Trend)
                    If R-squared ≤ 0.7: "↑" (Weak Upward Trend)
                If linear regression slope < 0 (downward trend):
                    If R-squared > 0.7: "↓↓" (Strong Downward Trend)
                    If R-squared ≤ 0.7: "↓" (Weak Downward Trend)
            If Mann-Kendall p-value > 0.05:
                "↔" (Range-bound)
            """
            if(len(series)<3):
                trend= f"↔ {round(maxv-minv,1)} bps"
            else:
                alpha=0.05
                r2_threshold=0.7

                mk_test_result = mk.original_test(series)
                p_value = mk_test_result.p
                if p_value > alpha:
                    trend= f"↔ {round(maxv-minv,1)} bps"
                else:
                    # Perform linear regression to get the slope and R-squared
                    # We create an index for the linear regression
                    x = np.arange(len(series))
                    slope, intercept, r_value, _, _ = linregress(x, series)
                    r_squared = r_value**2
                    # Classify based on slope and R-squared
                    if slope > 0:
                        if r_squared > r2_threshold:
                            trend= "↑↑"
                        else:
                            trend= "↑"
                    else:  # slope < 0
                        if r_squared > r2_threshold:
                            trend= "↓↓"
                        else:
                            trend= "↓"


            #roll data
            roll_down_val = roll_down_map.get(contract, 0)
            roll_up_val = roll_up_map.get(contract, 0)
            first_arrow = '▲' if roll_down_val < 0 else '▼' if roll_down_val > 0 else ''
            second_arrow = '▲' if roll_up_val < 0 else '▼' if roll_up_val > 0 else ''
            roll_combined = f"{first_arrow}{abs(roll_down_val):.1f} | {abs(roll_up_val):.1f}{second_arrow}"
            #risk rewqard
            if pd.isna(roll_down_val) or pd.isna(roll_up_val):
                risk_reward_diff_val = None
                risk_reward_ratio_val = None
                arrow= ''
            else:
                abs_rd = abs(roll_down_val)
                abs_ru = abs(roll_up_val)
                # Determine if it's a peak or a valley in the forward curve
                is_valley = (roll_down_val < 0 and roll_up_val <= 0)
                is_peak = (roll_down_val > 0 and roll_up_val >= 0)
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
                         arrow = '⬇' if roll_down_val > 0 else '⬆'
                    else:
                        arrow = '⬇' if roll_up_val > 0 else '⬆'
                    risk_reward_diff_val = abs(abs_rd - abs_ru)
                    
                    if (abs_rd== 0) & (abs_ru== 0):
                        risk_reward_ratio_val = 0
                    elif (abs_rd == 0) | (abs_ru == 0):
                        risk_reward_ratio_val = 99 if abs_ru+abs_ru > 0 else -99
                    else:
                        risk_reward_ratio_val = min(99, max(abs_rd, abs_ru) / min(abs_rd, abs_ru))
                        
        
            if risk_reward_ratio_val is not None:
                #print(abs_rd, abs_ru)
                risk_reward_combined = f"{arrow}{risk_reward_ratio_val:.1f} | {risk_reward_diff_val:.1f}"
            else:
                risk_reward_combined = ''
            
            #table formation
            table_data.append({
                "Contract": str(contract),
                "Latest Price": latest_price,
                "Last Settle":last_settle,
                "% Change": pct_change,
                "CoD": CoD,
                "percentile_rank": percentile_rank,
                "z_score": z_score,
                "max": maxv,
                "min": minv,
                "rangev": rangev,
                "trend": trend,
                "peaks_n_valleys": flag,
                "med": med,
                "mean": meanv,
                "std_dev": std_dev,
                "SparkLine": SparkLine,
                "Histogram": daily_changes,

                "roll_combined": roll_combined,
                "risk_reward_combined": risk_reward_combined ,
            })
        except Exception as inner_e:
            logging.warning(f"Skipping contract {contract}: {inner_e}")
            continue        

    # If no contracts had enough data, return an empty table
    if not table_data:
        return [], []
    table_df = pd.DataFrame(table_data)
 
    # Define the columns for the AG Grid table
    
    columnDefs = [
        {"field": "Contract", "headerName": f"{str_name}",  "filter": "agTextColumnFilter", "maxWidth": 125, "pinned": "left"},
        {"field": "Latest Price", "headerName": "Latest Price",  "type": "numericColumn", "valueFormatter": {"function": "d3.format(',.2f')(params.value)"} ,"maxWidth": 125, "headerTooltip": "Latest Price", "pinned": "left"},
        {"field": "Last Settle", "headerName": "Last Settle",  "type": "numericColumn", "valueFormatter": {"function": "d3.format(',.1f')(params.value)"}, "maxWidth": 125, "headerTooltip":"Last Settle", "hide": True},
        {"field": "CoD", "headerName": "CoD",  "type": "numericColumn", "valueFormatter": {"function": "d3.format(',.1f')(params.value)"}, "maxWidth": 100, "headerTooltip": "Change of day"},
        {"field": "% Change", "headerName": "% Change", "type": "numericColumn", "valueFormatter": {"function": "params.value == null ? '' : d3.format('+.0f')(params.value)"}, "maxWidth": 125, "headerTooltip":"% Change"},
        {"field": "percentile_rank", "headerName": "Rank",  "type": "numericColumn", "valueFormatter": {"function": "params.value == null ? '' : d3.format(',.0f')(params.value)"}, "maxWidth": 120, "headerTooltip":f"Percentile rank in {change_period}d"},
        {"field": "z_score", "headerName": "Z Score",  "type": "numericColumn", "valueFormatter": {"function": "d3.format(',.1f')(params.value)"}, "maxWidth": 120,"headerTooltip": f"Z Score of {change_period}d"},
        {"field": "roll_combined", "headerName": "Roll (Dn|Up)",  "type": "stringColumn", "maxWidth": 150, "headerTooltip": "Roll Dn | Up"},
        {"field": "risk_reward_combined", "headerName": "R/R (ratio|Diff)",  "type": "stringColumn", "maxWidth": 125, "headerTooltip": "Risk/ Reward Ratio | Diff"},
        {"field": "rangev", "headerName": "Range", "type": "numericColumn", "valueFormatter": {"function": "d3.format(',.1f')(params.value)"}, "maxWidth": 115, "headerTooltip": f"Range of {change_period}d"},
        {"field": "trend", "headerName": "Trend",  "type": "stringColumn", "maxWidth": 125, "headerTooltip": "Trend"},
        {"field": "peaks_n_valleys", "headerName": "Extremum",  "type": "stringColumn","maxWidth": 125, "headerTooltip": "Support | Resistance"},
        {"field": "SparkLine","headerName": f"SparkLine","cellRenderer": "agSparklineCellRenderer","cellRendererParams": {"sparklineOptions": {"type": "line","line": {"stroke": "#66c2a5", "strokeWidth": 2},"axis": {"stroke": "rgba(255, 255, 255, 1)", "strokeWidth": 3}}}, "minWidth": 250},
        {"field": "Histogram","headerName": f"Daily Change","cellRenderer": "agSparklineCellRenderer","cellRendererParams": {"sparklineOptions": {"type": "column", "fill": 'grey',"stroke": "#fc8d62","highlightStyle": {"fill": "#e34a33",  "stroke": None },"axis": {"stroke": "rgba(255, 255, 255, 0.5)", "strokeWidth": 0.2}}}, "minWidth": 250},
        {"field": "max", "headerName": "Max",  "type": "numericColumn", "valueFormatter": {"function": "d3.format(',.1f')(params.value)"}, "maxWidth": 120, "headerTooltip": f"Max of {change_period}d" },
        {"field": "min", "headerName": "Min",  "type": "numericColumn", "valueFormatter": {"function": "d3.format(',.1f')(params.value)"}, "maxWidth": 120, "headerTooltip": f"Min of {change_period}d" },
        {"field": "med", "headerName": "Med",  "type": "numericColumn", "valueFormatter": {"function": "d3.format(',.1f')(params.value)"}, "maxWidth": 120, "headerTooltip": "Median"},
        {"field": "mean", "headerName": "Mean",  "type": "numericColumn", "valueFormatter": {"function": "d3.format(',.1f')(params.value)"}, "maxWidth": 120, "headerTooltip": "Mean"},
        {"field": "std_dev", "headerName": "Std dev",  "type": "numericColumn", "valueFormatter": {"function": "d3.format(',.1f')(params.value)"}, "maxWidth": 120, "headerTooltip": "Std dev"},
        
    ]

    # Convert the final DataFrame to the rowData format and return
    rowData = table_df.to_dict('records')
    return rowData, columnDefs

def warning_plot_copy2(warning):
    fig = go.Figure()
    fig.add_annotation(
        #text="⚠ No 'Hike' cycle data available as per your criteria (no parent data)",
        text= warning,
        showarrow=False,
        font=dict(color="red", size=16),
        x=0.5, y=0.5, xref="paper", yref="paper",
        xanchor="center", yanchor="middle"
    )
    fig.update_layout(
        xaxis=dict(visible=True),
        yaxis=dict(visible=True)
    )
    fig.update_yaxes(fixedrange=True)
    fig.update_xaxes(fixedrange=True)
    return fig