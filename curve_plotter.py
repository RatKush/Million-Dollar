import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from curve_help import moving_average, bollinger_bands, maxmin_band, median_series, rolling_quantile_series
from str_cal import load_data, fill_missing_values, get_ratio, calculate_str, remove_outliers, rolling_bounds_filter,process_help_calculation
import str_cal as strtr

def init_plot(title):
    """
    Initialize Plotly figure with standardized layout.
    """
    fig = go.Figure()
    fig.update_layout(
        title=dict(text=title, x=0.5, y=0.99, xanchor="center", font=dict(size=16)),
        hovermode="x unified",
        legend=dict(
            x=0.5, y=0.95,
            orientation="h",
            xanchor="center",
            yanchor="bottom"
        ),
        height=500,
        margin=dict(l=10, r=10, t=30, b=20),
        dragmode="pan"
    )
    return fig


def add_series(fig, data, name, color=None, mode="lines+markers", dash=None, opacity=1.0, zorder=1,
                hovertemplate="%{y:.2f} @%{fullData.name}<extra></extra>"):
    """
    Add line or marker trace to Plotly figure.
    """
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data.values,
        mode=mode,
        name=name,
        line=dict(color=color, dash='solid'),
        opacity=opacity,
        hovertemplate=hovertemplate
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


def add_plot_study(fig, name, item, base_label=None, color=None, zorder=1):
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
            fig = add_series(fig, data=series, name=label,
                             color=item.get("color", color),
                             dash=item.get("dash", "dot"),
                             opacity=item.get("opacity", 1.0),
                             zorder=zorder,
                             hovertemplate=item.get("hovertemplate",
                                                     "%{y:.2f} @%{fullData.name}<extra></extra>"))
    elif item.get("type") == "band":
        band = item.get("data", {})
        fig = add_band(fig, upper=band.get("upper"), lower=band.get("lower"),
                       name=label, color=item.get("color", "rgba(180,180,250,0.3)"), zorder=zorder)
    return fig


def generate_curve_plot(str_df,plot_title,win_local,bb_std,quantile,Settle,date1="2025-06-05", date2="2024-09-25",  plot_flags=None):
    """
    Plot structure curve with optional studies (latest, settle, MA, BB, XN).
    """
    win_xn=win_local
    win_bb_ma= win_local
    

    fig = init_plot(plot_title)

    if plot_flags.get("Latest"):
        fig = add_plot_study(fig, "Latest", {"type": "line", "data": str_df.iloc[0], "color": "blue"}, zorder=1000)

    if plot_flags.get("Settle"):
        fig = add_plot_study(fig, f"settle(-{Settle})", {"type": "line", "data": str_df.iloc[Settle], "color": "gold"}, zorder=999)
    
    def safe_parse_date(date_str_or_obj_or_none):
        if date_str_or_obj_or_none is None:
            return None
        if isinstance(date_str_or_obj_or_none, str):
            try:
                return datetime.strptime(date_str_or_obj_or_none, "%Y-%m-%d")
            except ValueError:
                return None  # or raise an error if you want
        return date_str_or_obj_or_none 

    
    #print("flag",plot_flags.get("Date2"),"d2", date2, date2 in str_df.index )
    date1 = safe_parse_date(date1)
    if date1 is not None and date1 not in str_df.index: 
        print("Date1 {date1} is outside of time range or must be a weekend")
    if plot_flags.get("Date1") and date1 in str_df.index:
        leg= date1.strftime("%Y-%m-%d")
        fig = add_plot_study(fig, f"{leg}", {"type": "line", "data": str_df.loc[date1], "color": "grey"}, zorder=100)
    
    date2 = safe_parse_date(date2)
    if date2 is not None and date2 not in str_df.index:  
        print("Date 2 {date2} is outside of time range or must be a weekend")
    if plot_flags.get("Date2") and date2 in str_df.index:
        leg= date2.strftime("%Y-%m-%d")
        fig = add_plot_study(fig, f"{leg}", {"type": "line", "data": str_df.loc[date2], "color": "black"}, zorder=101)

    if plot_flags.get("MA"):
        ma = moving_average(str_df, win_bb_ma)
        fig = add_plot_study(fig, f"ma({win_bb_ma})", ma, zorder=110)

    if plot_flags.get("MED"):
        med = median_series(str_df, win_bb_ma)
        fig = add_plot_study(fig, f"med({win_bb_ma})", med, zorder=110)

    if plot_flags.get("quant_ser"):
        q_ser = rolling_quantile_series(str_df, win_bb_ma, quantile)
        fig = add_plot_study(fig, f"quantile({round(quantile)}%|{win_bb_ma})", q_ser, zorder=110) 

    if plot_flags.get("BB"):
        bb = bollinger_bands(str_df, win_bb_ma, bb_std)
        fig = add_plot_study(fig, f"bb({win_bb_ma}|{bb_std})", bb, zorder=10)

    if plot_flags.get("XN"):
        xn = maxmin_band(str_df, win_xn)
        fig = add_plot_study(fig, f"xn({win_xn})", xn, zorder=20)

    #fig.show(config={"scrollZoom": True})
    return fig






def plot_single_structure(series, str_name):
    # Ensure index is datetime for x-axis formatting
    if not pd.api.types.is_datetime64_any_dtype(series.index):
        series.index = pd.to_datetime(series.index, errors='coerce')

    if series.empty:
        return warning_plot_copy2(f"Series data not availbale (plot_single_structure_{str_name})")

    fig = go.Figure()
    series = pd.to_numeric(series, errors='coerce')
    series= rolling_bounds_filter(series, window=21, k=2.5)
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
        #title=dict(text=title, x=0.5, y=0.99, xanchor="center"),
        title={"text": f"{str_name}", "x": 0.5, "xanchor": "center", "font": {"size": 16}},
        #xaxis_title="Date",
        #yaxis_title="Structure Value",
        height=500,
        margin=dict(l=10, r=10, t=30, b=20),
        hovermode='x',
        xaxis=dict(showgrid=True, tickformat="%d-%m-%y"),
        #config={'displayModeBar': False}
    )
    fig.update_yaxes(fixedrange=True)
    fig.update_xaxes(fixedrange=True)
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
    sum_of_eases_hikes_series = compute_conditional_sum(S3_df)
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

