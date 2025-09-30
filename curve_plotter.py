import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime
import dash_bootstrap_components as dbc
import logging

from curve_help import moving_average, bollinger_bands, maxmin_band, median_series, rolling_quantile_series
from str_cal import  rolling_bounds_filter,process_help_calculation
from str_cal import curve_at_datex
from kde_help import get_rank
import pymannkendall as mk
from scipy.stats import linregress


DEFAULT_WINDOW = 21
DEFAULT_OUTLIER_K = 2.5
DEFAULT_LOOKBACK = 250

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



def generate_curve_plot(str_df: pd.DataFrame, raw_df: pd.DataFrame ,plot_flags: dict,comdty:str= "SR3",curve_len:int=20, str_name :str= "L6",Settle: int = None,date1=None,date2=None,win_local: int = 21,quantile: float = None,bb_std: float = None):
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
        if dt not in str_df.index:
            try:
                nearest_idx = str_df.index.get_indexer([dt], method="nearest")[0]
                snapped = str_df.index[nearest_idx]
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
    #
    if plot_flags.get("Settle") and Settle is not None:
        try:
            Settle= int(Settle)
            Settle = max(-len(str_df), min(Settle, len(str_df) - 1))
            Settle = max(-win_local, min(Settle, win_local - 1))
            out_ser = raw_df.iloc[Settle] if raw_df.shape[0] > Settle else None
            settle_row = curve_at_datex(out_ser, comdty, str_name, curve_len)
            fig = add_plot_study(fig, name=f"Settle(-{Settle})",item={"type": "line", "data": settle_row, "color": "gold"},show_values=0)
        except Exception as e:
            logging.warning(f"Skipping Settle: {e}")

    if plot_flags.get("Date1") and date1 is not None:
        leg = date1.strftime("%Y-%m-%d")
        date_curve= curve_at_datex(raw_df.loc[date1], comdty, str_name, curve_len)
        fig = add_plot_study(fig, leg,{"type": "line", "data": date_curve, "color": "grey"},show_values=0)

    if plot_flags.get("Date2") and date2 is not None:
        leg = date2.strftime("%Y-%m-%d")
        date_curve= curve_at_datex(raw_df.loc[date2], comdty, str_name, curve_len)
        fig = add_plot_study(fig, leg,{"type": "line", "data": date_curve, "color": "darkgrey"},show_values=0)

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


##########################################################################  tab 2_1 table  ##############################################################
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

########################################################################## tab 2 #####################################################################################
def get_button_class(is_active: bool) -> str:
    base = "tab-button me-2"
    return base + " selected" if is_active else base

def build_button(label, id, active=False):
    return dbc.Button(
        label,
        id=id,
        className=get_button_class(active), 
        n_clicks=0
    )




def plot_single_structure(series, str_name):

    if series.empty:
        print("empty series")
        return warning_plot_copy2(f"⚠ Series data not availbale (plot_single_structure_{str_name})")
    # Ensure index is datetime for x-axis formatting
    if not pd.api.types.is_datetime64_any_dtype(series.index):
        #print("plot single",series.index)
        series.index = pd.to_datetime(series.index, unit='D', origin='1899-12-30', errors='coerce')

    

    fig = go.Figure()
    series = pd.to_numeric(series, errors='coerce')
    series= rolling_bounds_filter(series, window=21, k=2)
    #print(series.max)
    #series= remove_outliers(series, 0.01, 0.99)
    #print(series)
    #print(series.loc["2024-01-17"])
    # Add horizontal line at y = y0 parallel to x axis
    latest_x = series.index[0]
    latest_y = series.values[0]
    y0 = latest_y  #latest level
   
    fig.add_shape(
        type="line",
        x0=min(series.index), x1=max(series.index),
        y0=y0, y1=y0,
        line=dict(color="red", width=1, dash="solid"),
        #name="Horizontal Line"
    )


    fig.add_trace(go.Scatter(
        x=series.index,
        y=series.values,
        name=str_name,
        mode='lines',
        line=dict(
            color='blue',
            dash='solid'
        ),
        connectgaps=False,  # Ensures NaNs are not connected
        opacity=1,
        hovertemplate='%{y:.1f}<extra></extra>'  # <-- force numeric format
    ))
    
    

    fig.add_annotation(
        x=latest_x,
        y=latest_y,
        text= f"<b>{latest_y:.2f}</b>",       # same formatting as hover
        showarrow=True,
        arrowhead=0,
        arrowsize=1,
        ax=20,
        ay=0,
        font=dict(
            family="Arial",
            size=12,
            color="white",
        ),
        align="center",
        bgcolor="blue",     # match hover background
        #bordercolor="rgba(0, 0, 0, 0.8)", # match hover border
        #borderwidth=1,
        #borderpad=4,
        opacity=0.95
    )

    latest_percentile= get_rank(series , y0)
    #print(y0, series.head(), latest_percentile)
    fig.add_annotation(
        x=latest_x,
        y=y0,
        text=f"Pctl: ({str(round(latest_percentile))}%)",
        showarrow=False,
        xshift=10,
        yshift=20,
        font=dict(size=10, color="grey")
    )


    # Enable cross‑hair spikes
    fig.update_xaxes(
        showspikes=True,
        spikemode='across',
        spikecolor='grey',
        spikethickness=1,
        spikesnap='cursor'
    )
    fig.update_yaxes(
        showspikes=True,
        spikemode='across',
        spikecolor='grey',
        spikethickness=1,
        spikesnap='cursor'
    )
    fig.update_layout(
        #title=dict(text=title, x=0.5, y=0.90, xanchor="center"), font=dict(size=14,  color= "#1f2128")
        title={"text": f"{str_name}", "x": 0.5,"y":0.99, "xanchor": "center", "font": {"size": 14, "color": "#1f2128"}},
        #xaxis_title="Date",
        #yaxis_title="Structure Value",
        height=450,
        margin=dict(l=10, r=10, t=15, b=8),
        hovermode='x',
        xaxis=dict(showgrid=True, tickformat="%d-%m-%y"),
        #config={'displayModeBar': False}
    )
    #fig.update_yaxes(fixedrange=True)
    #fig.update_xaxes(fixedrange=True)
    return fig


#If the first value is positive or zero, sum positive values only — stop if a negative is found (but allow the first one even if it’s negative).
#If the first value is negative, sum negative values only — stop if a positive is found (but allow the first one even if it’s positive).
def row_logic_for_eases_hikes(row, check_window=4, max_cols=8):
    values = row.values[:max_cols]
    init_sum = sum(values[:check_window])
    total = 0
    if init_sum >= 0:                       # We're summing positive values, until a negative appears (except at index 0)
        for i, val in enumerate(values):
            if val < 0 and i != 0:
                break
            total += val
    else:                                   # We're summing negative values, until a positive appears (except at index 0)
        for i, val in enumerate(values):
            if val > 0 and i != 0:
                break
            total += val

    return total

def compute_conditional_sum(df, max_cols=8):
    return df.apply(lambda row: row_logic_for_eases_hikes(row, max_cols), axis=1)

def cal_sum_of_eases_hikes(out_df, comdty, lookback_prd):
    S3_df, comdty = process_help_calculation(comdty, out_df, "S3", lookback_prd, 15)
    sum_of_eases_hikes_series = compute_conditional_sum(S3_df,8)
    #print(len(sum_of_eases_hikes_series))
    sum_of_eases_hikes_series= sum_of_eases_hikes_series.head(lookback_prd)
    index = out_df.index[:lookback_prd]
    return pd.Series(sum_of_eases_hikes_series, index=index)

def cal_sum_of_same_sign_meets(out_df, comdty, lookback_prd):
    Out_df, comdty = process_help_calculation(comdty, out_df, "Out", lookback_prd, 20)
    sum_of_eases_hikes_series = compute_conditional_sum(Out_df,20)
    
    # print("lb", lookback_prd)
    lenfinal= min(lookback_prd, len(sum_of_eases_hikes_series), len(out_df))
    sum_of_eases_hikes_series= sum_of_eases_hikes_series.iloc[:lenfinal]
    out_df= out_df.iloc[:lenfinal]
    return pd.Series(sum_of_eases_hikes_series, index=out_df.index)





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


##################################### tab2_2 #############################################################
def plot_chart_2_2():
    fig = go.Figure()
    # Enable cross‑hair spikes
    fig.update_xaxes(
        showspikes=True,
        spikemode='across',
        spikecolor='grey',
        spikethickness=1,
        spikesnap='cursor'
    )
    fig.update_yaxes(
        showspikes=True,
        spikemode='across',
        spikecolor='grey',
        spikethickness=1,
        spikesnap='cursor'
    )
    fig.update_layout(
        height=450,
        margin=dict(l=10, r=10, t=10, b=20),
        hovermode='x',
        xaxis=dict(showgrid=True, tickformat="%d-%m-%y"),
        #config={'displayModeBar': False}
    )
    # fig.update_yaxes(fixedrange=True)
    # fig.update_xaxes(fixedrange=True)
    return fig


def add_chart_2_2(fig, series,corr, legend, color= "#f58231", axis= "1st"): #purple
    if series.empty or series.dropna().empty: 
        print("empty series")
        return
    # Ensure index is datetime for x-axis formatting



    if not pd.api.types.is_datetime64_any_dtype(series.index):
        #print("plot single",series.index)
        series.index = pd.to_datetime(series.index, unit='D', origin='1899-12-30', errors='coerce')

    series = pd.to_numeric(series, errors='coerce')
    series= rolling_bounds_filter(series, window=21, k=2.5)

    # Add horizontal line at y = y0 parallel to x axis
    latest_x = series.index[0]
    latest_y = series.values[0]
    y0 = latest_y  #latest level
    latest_percentile= get_rank(series , y0)
    fig.add_shape(
        type="line",
        x0=min(series.index), x1=max(series.index),
        y0=y0, y1=y0,
        line=dict(color="red", width=1, dash="solid"),
    )


    fig.add_trace(go.Scatter(
        x=series.index,
        y=series.values,
        name= legend,
        mode='lines',
        line=dict(
            color= color,
            dash='solid'
        ),
        connectgaps=False,  # Ensures NaNs are not connected
        opacity=1,
        hovertemplate='%{y:.0f}<extra></extra>'  # <-- force numeric format
    ))
    
    

    fig.add_annotation(
        x=latest_x,
        y=latest_y,
        text= f"<b>{str(round(latest_y))}</b>",       # same formatting as hover
        showarrow=True,
        arrowhead=0,
        arrowsize=1,
        ax=20,
        ay=0,
        font=dict(
            family="Arial",
            size=12,
            color="white",
        ),
        align="center",
        bgcolor="blue",     # match hover background
        opacity=0.95
    )
    
    latest_percentile= get_rank(series , y0)
    #print(y0, series.head(), latest_percentile)
    fig.add_annotation(
        x=latest_x,
        y=y0,
        text=f"Pctl: ({str(round(latest_percentile))}%)",
        showarrow=False,
        xshift=5,
        yshift=25,
        font=dict(size=10, color="grey")
    )
    #print(corr["mean_rolling_correlation"], corr["distance_correlation"])
    if corr['mean_rolling_correlation'] is not None:
        fig.add_annotation(
            x=latest_x,
            y=y0,
            text=f"Corr: ({round(corr['mean_rolling_correlation'],1)})",
            showarrow=False,
            xshift=5,
            yshift= 15,
            font=dict(size=10, color="grey")
        )

    fig.update_layout(
        legend=dict(
            orientation="h",          # horizontal legend
            yanchor="bottom",
            y=0.96,                   # position just above the top of the chart
            xanchor="center",
            x=0.5
        )
    )

    return fig




def Out_tab2_2(raw_df,comdty, str_number, lookback_prd):
    if raw_df.empty:
        return pd.Series()

    max_cols = raw_df.shape[1]
    max_rows = raw_df.shape[0]
    actual_lookback = min(lookback_prd, max_rows)
    if str_number > max_cols:
        str_number = max_cols
    series = raw_df.iloc[:actual_lookback, str_number - 1].copy()
    return rolling_bounds_filter(series, window= DEFAULT_WINDOW, k= DEFAULT_OUTLIER_K)

def S12_tab2_2(out_df, n, lookback_prd):
    if out_df.empty:
        return pd.Series()
    if n + 3 >= out_df.shape[1]:
        print( "n+3 column index exceeds DataFrame width")
        return pd.Series()
    actual_lookback = min(lookback_prd, out_df.shape[0])

        # Extract both columns
    col1 = out_df.iloc[:actual_lookback, n-1].copy()
    col2 = out_df.iloc[:actual_lookback, n+3].copy()

    # Replace None/NaN with 0 in col1
    col1 = col1.fillna(100) #handling ED part where 1st out is not there hence 2nd out itself carries all the eases/hikes

    # Compute series
    series = (col1 - col2) * 100
    #print(series.head(), len(series))
    series= rolling_bounds_filter(series, window= DEFAULT_WINDOW, k= DEFAULT_OUTLIER_K)
    return series

def L6_tab2_2(out_df, n, lookback_prd):
    if n + 2 >= out_df.shape[1]:
        print( "n+2 column index exceeds DataFrame width")
        return pd.series()
    series = (out_df.iloc[:lookback_prd,n-1] - 2* out_df.iloc[:lookback_prd, n+1]+ out_df.iloc[:lookback_prd, n+3])*100
    #print(series.head(), len(series))
    series= rolling_bounds_filter(series, window= DEFAULT_WINDOW, k= DEFAULT_OUTLIER_K)
    return series


import numpy as np
def compute_correlation_parameters(series1: pd.Series, series2: pd.Series, rolling_window: int = 21):
    """
    The window size for the rolling correlation calculation is 21
    'mean_rolling_correlation': The average of the rolling Pearson correlation.
                            [-1,+1] [perfect inverse correlation, perfect positive correlation]
    'distance_correlation' : captures both linear and non-linear relationships.
                            [0,1] (statistical independence) to 1.
    """
    
        
    if not isinstance(series1, pd.Series) or not isinstance(series2, pd.Series):
        print( "Inputs must be pandas Series.")
        return {"mean_rolling_correlation": None,"distance_correlation": None}
    #print(f"Input series must have the same length {len(series1)}, {len(series2)}")
    if len(series1) != len(series2):
        print(f"Input series must have the same length {len(series1)}, {len(series2)}")
        return {"mean_rolling_correlation": None,"distance_correlation": None}

    if len(series1) < rolling_window:
        print(f"Input series length ({len(series1)}) cannot be less than the rolling window size ({rolling_window}).")
        return {"mean_rolling_correlation": None,"distance_correlation": None}
    
    series1 = pd.to_numeric(series1, errors="coerce")
    series2 = pd.to_numeric(series2, errors="coerce")
    series1.replace([np.inf, -np.inf], np.nan, inplace=True)
    series2.replace([np.inf, -np.inf], np.nan, inplace=True)
    # This creates a new series where each point is the correlation of the preceding 'window' data points.
    rolling_corr = series1.rolling(window=rolling_window).corr(series2)
    # The first (window - 1) values will be NaN, so we drop them before calculating the mean.
    mean_rolling_corr = rolling_corr.dropna().mean()

    # # --- 3. Distance Correlation (dCor) ---
    # # dCor is powerful because it is zero if and only if the series are truly independent.
    # # It captures non-linear and non-monotonic relationships that standard correlation would miss.
    # dist_corr = dcor.distance_correlation(series1.values, series2.values)
    dist_corr=0

    return {
        'mean_rolling_correlation': mean_rolling_corr,
        'distance_correlation': dist_corr
    }


######################################################## 2_3 ################################
def plot_chart_2_3():
    fig = go.Figure()
    # Enable cross‑hair spikes
    
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#ececec",
        #zeroline=False,
        #showspikes=True,
        spikemode='across',
        spikecolor='grey',
        spikethickness=1,
        spikesnap='cursor'
    )
    fig.update_yaxes(
        showgrid=True,
        showspikes=True,
        gridcolor="#ececec",
        #showspikes=True,
        spikemode='across',
        spikecolor='grey',
        spikethickness=1,
        spikesnap='cursor'
    )
    fig.update_layout(
        height=450,
        margin=dict(l=10, r=10, t=10, b=20),
        hovermode='closest',
        #xaxis=dict(showgrid=True, tickformat="%d-%m-%y"),
        legend=dict(
            orientation="h",          # horizontal legend
            yanchor="bottom",
            y=0.96,                   # position just above the top of the chart
            xanchor="center",
            x=0.5
        )
        #config={'displayModeBar': False}
    )
    fig.update_yaxes(fixedrange=True)
    fig.update_xaxes(fixedrange=True)
    return fig


def add_chart_2_3(fig, series_Y, series_base, legend, color= "#f58231", axis= "1st"): #purple
    
    if series_Y.empty or series_Y.dropna().empty or series_base.empty or series_base.dropna().empty: 
        print("empty series")
        return
    if len(series_Y) != len(series_base):
        print(f"Input series must have the same length {len(series_Y)}, {len(series_base)}")
        return
    
    series_Y = pd.to_numeric(series_Y, errors='coerce')
    series_Y= rolling_bounds_filter(series_Y, window=21, k=2)
    series_base = pd.to_numeric(series_base, errors='coerce')
    series_base= rolling_bounds_filter(series_base, window=21, k=2)


   
    df = pd.DataFrame({'x': series_base, 'y': series_Y}).dropna()
    fig.add_trace(go.Scatter(
        x= df['x'],
        y= df['y'],
        name= legend,
        mode='markers',
        marker=dict(
            size=8,
            color= color,
            symbol='circle',
            opacity=1,
        ),
        hovertemplate=f"<b>{legend}</b><br>X : %{{x:.0f}}<br>Y : %{{y:.0f}}<extra></extra>",
        customdata=df.index
    ))
     
    # --- Add Optional Mean Lines for Context ---
    mean_x = df['x'].mean()
    mean_y = df['y'].mean()
    
    # Vertical mean line
    fig.add_shape(type="line", x0=mean_x, x1=mean_x, y0=df['y'].min(), y1=df['y'].max(),
                    line=dict(color="grey", width=1.5, dash="dash"))
    # Horizontal mean line
    fig.add_shape(type="line", x0=df['x'].min(), x1=df['x'].max(), y0=mean_y, y1=mean_y,
                    line=dict(color="grey", width=1.5, dash="dash"))
        

    latest_x = series_base.iloc[0]
    latest_y = series_Y.iloc[0]
    # Add a new trace specifically for the single point
    fig.add_trace(go.Scatter(
        x=[latest_x],  # Must be in a list or array
        y=[latest_y],  # Must be in a list or array
        mode='markers',
        name='Latest', # This will appear in the legend
        marker=dict(
            size=14,            # Make it larger to stand out
            color='red',        # Use a distinct color
            symbol='star',      # Use a different symbol (e.g., star, diamond)
            #line=dict(width=2, color='darkred') # Add a border to the marker
        ),
        showlegend=False,
        hovertemplate="<b>Latest</b><br>X: %{x:.1f}<br>Y: %{y:.1f}<extra></extra>"
    ))




    fig.update_layout(
        legend=dict(
            orientation="h",          # horizontal legend
            yanchor="bottom",
            y=0.96,                   # position just above the top of the chart
            xanchor="center",
            x=0.5
        )
    )

    return fig