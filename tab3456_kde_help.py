import pandas as pd
import numpy as np
from scipy.stats import gaussian_kde, mode
import plotly.graph_objects as go
from str_cal import process_help_calculation
from dash import dcc, html
import dash_bootstrap_components as dbc

# ##############################shared control panel for all 4 kde plot cntrol tab3---- tab6################################

kde_options=[
        {"label": "Latest", "value": "Latest"},
        {"label": "Band 68%", "value": "band68"},
        {"label": "Band 95%", "value": "band95"},
        {"label": "mean ± 1σ", "value": "bb1"},
        {"label": "mean ± 2σ", "value": "bb2"},
        {"label": "Median", "value": "med"},
        {"label": "% Line", "value": "pc_line"},
        {"label": "Val Line", "value": "val_line"},  
    ],

def get_kde_controls():
    view= html.Div([
        html.H5("Plot Controls", style={"color":"#c0c4cc","textAlign": "center", "padding": "8px 16px","backgroundColor": "#2b2e35","fontWeight": "500","fontSize": "16px","border": "1px solid #3a3f4b",  "borderTopLeftRadius": "8px",  "borderTopRightRadius": "8px", "margin": "0"}
        ),

        # --- Cycle Classification Section (Wide, Cleaner) ---
        html.Div([
            html.Div("Cycle Classification", className="fw-bold small px-2 py-1", style={
                "backgroundColor": "#1f2128",
                "borderBottom": "1px solid #3a3f4b",
                "borderTopLeftRadius": "6px",
                "borderTopRightRadius": "6px",
                "color": "#c0c4cc",
                "fontWeight": "500",
                "textAlign": "center",
                "padding": "8px 16px",
            }),

            html.Div([

                html.Div([
                    html.Label("Base Str", className="form-label", style={"width": "68%", "marginBottom": 0}),
                    dcc.Input(id="base-str-input", type="text", value="S3", debounce=True, placeholder="S3/L3",
                            className="form-control form-control-sm", style={"width": "32%"})
                ], className="d-flex justify-content-between mb-2"),

                html.Div([
                    html.Label("Cons to Sum", className="form-label", style={"width": "70%", "marginBottom": 0}),
                    dcc.Input(id="sum-first-n-base-input", type="number", value=4, min=1, step=1, debounce=True,
                            className="form-control form-control-sm", style={"width": "30%"})
                ], className="d-flex justify-content-between mb-2"),

                html.Div([
                    html.Label("Hike Thrshld", className="form-label", style={"width": "68%", "marginBottom": 0}),
                    dcc.Input(id="hike-threshold-input", type="number", value=50, step=5, debounce=True,
                            className="form-control form-control-sm", style={"width": "32%"})
                ], className="d-flex justify-content-between mb-2"),

                html.Div([
                    html.Label("Ease Thrshld", className="form-label", style={"width": "68%", "marginBottom": 0}),
                    dcc.Input(id="ease-threshold-input", type="number", value=-50, step=5, debounce=True,
                            className="form-control form-control-sm", style={"width": "32%"})
                ], className="d-flex justify-content-between mb-1")

            ], style={"padding": "12px 10px 10px 10px"})

        ],style={"border": "1px solid #3a3f4b","borderRadius": "6px","backgroundColor": "#2b2e35","margin": "10px 0 18px 0"}),


        dbc.Checklist(
            id='kde-flags-shared',
            options=kde_options,
            value=["Latest","med", "band68", "band95"],
            switch=True,
            className="px-3 mb-3"
        ),
      

        html.Div([
            html.Label("Val Line", className="form-label", style={"width": "68%"}),
            dcc.Input(id="kde-val-line-shared", type="number", value=0, debounce=True, className="form-control form-control-sm", style={"width": "32%"})
        ], className=" px-3 mb-2 hidden-row", id="kde-val-row"),

        html.Div([
            html.Label("% Line", className="form-label", style={"width": "68%"}),
            dcc.Input(id="kde-pc-line-shared", type="number", value=95, min=0, max=100, step=1, debounce=True, className="form-control form-control-sm", style={"width": "32%"})
        ], className=" px-3 mb-2 hidden-row", id="kde-pc-row")

    ], className="control-panel-1")
    return view


    


def create_kde_tab(lbl, value, loading_id, plot_id):
    view= dcc.Tab(label= lbl, value=value,
        style={"height": "42px","borderRadius": "8px 8px 0 0","padding": "8px 16px","marginRight": "4px","backgroundColor": "#2b2e35","color":  "#c0c4cc","fontWeight": "500","border": "1px solid #3a3f4b","borderBottom": "none","transition": "background-color 0.3s, color 0.3s"
            },
        selected_style={"height": "45px","borderRadius": "8px 8px 0 0","padding": "8px 16px","backgroundColor": "#1f2128","color": "#ffffff","fontWeight": "600","border": "1px solid #5e636e","borderBottom": "none","boxShadow": "0px -2px 6px rgba(0, 0, 0, 0.4)"
            },
        children=[
            html.Div([  #####css-for-control panel
                dbc.Row([
                    dbc.Col(dcc.Loading(
                        id=loading_id,
                        type="circle", 
                        children=html.Div(dcc.Graph(id=plot_id, config={'scrollZoom': True, 'displayModeBar': False}),className="border p-2 my-2 rounded")
                    ), width=10),
                ])
            ],style={"position": "relative"})##########css-for-control panel
        ])
    return view


##############################################
# PLOT INITIALIZATION AND BASIC UTILITIES
##############################################

def initiate_plot(title):
    """
    Initialize a Plotly figure with consistent styling.
    """
    fig = go.Figure()
    fig.update_layout(
        #xaxis_title='Value',
        #yaxis_title='Density',
        title={"text": f"{title}", "x": 0.5,"y":0.99, "xanchor": "center", "font": {"size": 14, "color": "#1f2128"}},
        #title=dict(text=title, x=0.5, y=0.99, xanchor="center",  "font": {"size": 14, "color": "#1f2128"}),
        legend=dict(x=0.5, y=0.96, orientation="h", xanchor="center", yanchor="bottom"),
        height=530,
        margin=dict(l=10, r=10, t=30, b=20),
        dragmode="pan"
    )
    return fig





def small_window_stats(series, small_window=21, std_multi=1):
    """
    Compute short-window rolling stats (mean, std, min, max, BB).
    """
    if len(series) < small_window:
        raise ValueError("Series too short for window")
    recent = series.iloc[:small_window]
    mean = recent.mean()
    std = recent.std()
    return {
        "mean": mean,
        "std": std,
        "min": recent.min(),
        "max": recent.max(),
        "bb": {mean - std_multi * std, mean + std_multi * std}
    }


def compute_stats(series):
    """
    Compute distribution statistics for the series.
    """
    series = pd.to_numeric(series, errors='coerce').dropna()
    if len(series) < 2:
        return None

    std_val = series.std()
    z_val = np.nan
    if std_val and not np.isnan(std_val):
        z_val = round((series.iloc[0] - series.mean()) / std_val, 1)

    return {
        "skew": round(series.skew(), 1),
        "kurt": round(series.kurt(), 1),
        "z":  z_val,
        "mean": series.mean(),
        "med": np.median(series),
        "std": round(series.std(), 1)
    }


def get_percentile(series, pc):
    series = pd.to_numeric(series, errors='coerce').dropna()
    return np.percentile(series, pc).round(1)


def get_rank(series, val):
    series = series.dropna().values
    if len(series) == 0:
        return np.nan
    rank = (np.sum(series < val) + 0.5 * np.sum(series == val)) / len(series)
    return rank * 100


def plot_kde(fig, series):
    series = pd.to_numeric(series, errors='coerce').dropna()
    if len(series) >= 2:
        kde = gaussian_kde(series)
        x_vals = np.linspace(series.min(), series.max(), 300)
        kde_vals = kde(x_vals)
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=kde_vals,
            mode='lines',
            name='KDE',
            line=dict(color='royalblue', width=3),
            showlegend=False,
            hovertemplate='val: %{x:.1f}'
        ))
    else:
        print("Not enough data for KDE. Skipping...")
    return fig


def add_vline(fig, x, color='black', dash='solid', width=2, text=None, position="top right", opacity=1.0, showlegend=True):
    y_vals = [y for trace in fig.data if 'y' in trace for y in trace.y]
    y_min, y_max = (0, 1) if not y_vals else (np.nanmin(y_vals), np.nanmax(y_vals))
    fig.add_trace(go.Scatter(
        x=[x, x],
        y=[y_min, y_max],
        mode='lines',
        line=dict(color=color, dash=dash, width=width),
        name=text if showlegend else '',
        showlegend=showlegend,
        hoverinfo='skip',
        opacity=opacity
    ))
    return fig


def add_band_mask(fig, lower_pct, upper_pct, kde_trace_name, name):
    kde_trace = next((t for t in fig.data if isinstance(t, go.Scatter) and t.name == kde_trace_name), None)
    if kde_trace is None:
        raise ValueError(f"No trace named '{kde_trace_name}' found.")
    x_vals, kde_vals = np.array(kde_trace.x), np.array(kde_trace.y)
    mask = (x_vals >= lower_pct) & (x_vals <= upper_pct)
    fig.add_trace(go.Scatter(
        x=np.concatenate([x_vals[mask], x_vals[mask][::-1]]),
        y=np.concatenate([kde_vals[mask], np.zeros_like(kde_vals[mask])]),
        fill='toself',
        fillcolor='rgba(137, 207, 240, 0.3)',
        line=dict(color='rgba(255,255,255,0)'),
        hoverinfo='skip',
        showlegend=True,
        name=name
    ))
    return fig









def classify_cycle(series,comdty, out_df,lookback_prd, base_str, sum_first_n_base,  hike_threshold=50, dovish_threshold=-50):
    """
    Classify points in the series as part of hike, ease, or sideway cycles
    based on cumulative values of the first 4 elements of the S3 structure.
    """
    hike_cycle = pd.Series(dtype='object')
    ease_cycle = pd.Series(dtype='object')
    side_ways = pd.Series(dtype='object')

    ##base_df= series
    base_df, comdty= process_help_calculation(comdty, out_df, base_str, lookback_prd, 20)
    
    for date, row in base_df.iterrows():
        if base_df.index.min() > date:
            break
        score = row.iloc[:sum_first_n_base].sum()
        if pd.notna(date):
            str_val = series.get(date.strftime('%Y-%m-%d'))
        else:
            str_val = None
        
        if score > hike_threshold:
            hike_cycle.at[date] = str_val
        elif score < dovish_threshold:
            ease_cycle.at[date] = str_val
        else:
            side_ways.at[date] = str_val

    return hike_cycle, ease_cycle, side_ways






def plot_main_kde(plot_flags,Comdty, str_name,str_number, lookback_prd, series, pc_line, val_line):
    """
    Plot KDE with optional overlays (median, BB, local stats, value line).
    """
    lbp = min(len(series), lookback_prd)
    #print(len(series))
    title = f"{Comdty}{str_name}({str_number})@{lbp}d"
    latest_value = round(series.iloc[0], 2)
    stats = compute_stats(series)

    #print(Comdty, str_name,str_number, lookback_prd, pc_line, val_line, local_win, local_std)
    # print("Name", Comdty+ series.name, "latest value", latest_value, " @latest date", series.index[0].strftime("%d-%m-%Y"), "last date",series.index[-1].strftime("%d-%m-%Y") , "data ct", len(series))
    # print("describe", series.describe().round(1))
    # print("skewness:", stats['skew'], "Kurtness:", stats['kurt'], "Z_score:", stats['z'], "std:", stats['std'])
    
    fig = initiate_plot(title)
    
    if plot_flags.get("KDE", 1):
        fig = plot_kde(fig, series)

    # if stats is None:
    #     return fig

    if plot_flags.get("bb1", 1):
        add_band_mask(fig, stats['mean'] - stats['std'], stats['mean'] + stats['std'], "KDE", name=f"bb (σ=1)")

    if plot_flags.get("bb2", 1):
        add_band_mask(fig, stats['mean'] - 2 * stats['std'], stats['mean'] + 2 * stats['std'], "KDE", name=f"bb (σ=2)")


    #print(stats['mean'] - 2 * stats['std'], stats['mean'] + 2 * stats['std'])
    if plot_flags.get("band68", 1):
        l= get_percentile(series, 17)
        u= get_percentile(series, 83)
        add_band_mask(fig, l, u, "KDE", name=f"band68")

    if plot_flags.get("band95", 1):
        l= get_percentile(series, 2.5)
        u= get_percentile(series, 97.5)
        add_band_mask(fig, l, u, "KDE", name=f"band95")

    # if plot_flags.get("mean", 1):
    #     val = round(stats['mean'], 1)
    #     rank = round(get_rank(series, val))
    #     add_vline(fig, val, color='#1A7F37', dash='dash', text=f"Mean({val} | {rank}%)")


    if plot_flags.get("med", 1):
        val = round(stats['med'], 1)
        rank = round(get_rank(series, val))
        add_vline(fig, val, color='#7B1FA2', dash='dash', text=f"Med({val} | {rank}%)")
#     [
#     "#C00000", "#E66100", "#B8860B", "#1A7F37", "#008B8B",
#     "#005BBB", "#483D8B", "#7B1FA2", "#AD1457", "#404040"
# ] #colors
   
    if plot_flags.get("pc_line", 1):
        if pc_line is not None:
            try:
                percentile_val = get_percentile(series, pc_line)
                pc_line = float(pc_line)
                add_vline(fig, percentile_val, color="#07031D", dash='dash', text=f"Val ({percentile_val} | {pc_line}%)")
            except (ValueError, TypeError):
                # ignore bad inputs (non-numeric)
                pass

    if plot_flags.get("val_line", 1):
        if val_line is not None:
            try:
                val = float(val_line)

                # Clamp to series range
                if val < series.min():
                    val = series.min()
                elif val > series.max():
                    val = series.max()

                # Rank & rounding
                rank = round(get_rank(series, val))
                val = round(val, 1)

                add_vline(fig, val, color='#005BBB', dash='dash', text=f"Val ({val} | {rank}%)")
            except (ValueError, TypeError):
                # ignore bad inputs (non-numeric)
                pass

    # local_win = 21 if local_win is None else int(local_win)
    # local_std = 1 if local_std is None else int(local_std)    
    # small_win = small_window_stats(series, small_window=local_win, std_multi=local_std)

    # if plot_flags.get("local_mean", 1):
    #     val = round(small_win['mean'], 1)
    #     add_vline(fig, small_win['mean'], color="#853910", dash='dash', width=1.5, text=f"local mean@{local_win}d ({val})")

    # if plot_flags.get("local_xn", 1):
    #     val_min = round(small_win['min'], 1)
    #     val_max = round(small_win['max'], 1)
    #     add_vline(fig, small_win['min'], color='orange', dash='dash', width=2, text=f"local min@{local_win}d ({val_min})")
    #     add_vline(fig, small_win['max'], color='orange', dash='dash', width=2, text=f"local max@{local_win}d ({val_max})")

    # if plot_flags.get("local_bb", 1):
    #     add_band_mask(fig, small_win['mean'] - small_win['std'], small_win['mean'] + small_win['std'], "KDE", name=f"local bb@{local_win}d (σ=1)")

    if plot_flags.get("Latest", 1):
        latest_value = round(series.iloc[0], 2)
        rank = round(get_rank(series, latest_value))
        add_vline(fig, latest_value, color='red', width=3, text=f"Latest({latest_value} | {rank}%)")

    #fig.show(config={"scrollZoom": True})
    return fig

 # for sub- series #####################################################################################################################
def plotted_sub_KDE(plot_flags, sub_series,title,cycle_name, latest_val, pc_line, val_line):
    """
    Plot KDE distribution and overlays for a specific cycle subset.
    """
    #print(cycle_name, sub_series)
    if sub_series is None :
        return warning_plot_copy("No data found (failed in plotted_sub_kde)")
    if isinstance(sub_series, list):
        sub_series = pd.Series(sub_series)
 
    fig = initiate_plot(title)
    len_sub_series= len(sub_series)
    if (sub_series is None) or (sub_series.empty) or (len(sub_series)<2):
        text= f"⚠ No {cycle_name} cycle data available as per your criteria-({len_sub_series}) points found (returned by plotted)"
        return warning_plot_copy(text)    
        
    if plot_flags.get("KDE", 1):
        fig = plot_kde(fig, sub_series)

    stats = compute_stats(sub_series)
    # if stats is not None:
    #     print(f"{cycle_name} | len={len(sub_series)}, non-NaN={sub_series.count()}, skew={stats['skew']}, kurt={stats['kurt']}, z={stats['z']}, std={stats['std']}")

    if plot_flags.get("bb1", 1) and stats is not None:
        add_band_mask(fig, stats['mean'] - stats['std'], stats['mean'] + stats['std'], "KDE", name=f"bb (σ=1)")

    if plot_flags.get("bb2", 1) and stats is not None:
        add_band_mask(fig, stats['mean'] - 2 * stats['std'], stats['mean'] + 2 * stats['std'], "KDE", name=f"bb (σ=2)")

    if plot_flags.get("band68", 1):
        l= get_percentile(sub_series, 17)
        u= get_percentile(sub_series, 83)
        #print("l", l, "u", u)
        add_band_mask(fig, l, u, "KDE", name=f"band68")

    if plot_flags.get("band95", 1):
        l= get_percentile(sub_series, 2.5)
        u= get_percentile(sub_series, 97.5)
        add_band_mask(fig, l, u, "KDE", name=f"band95")

    # if plot_flags.get("mean", 1):
    #     val = round(stats['mean'], 1)
    #     rank = round(get_rank(sub_series, val))
    #     add_vline(fig, val, color='#1A7F37', dash='dash', text=f"Mean({val} | {rank}%)")

    if plot_flags.get("med", 1) and stats is not None:
        val = round(stats['med'], 1)
        rank = round(get_rank(sub_series, val))
        add_vline(fig, stats['med'], color='#7B1FA2', dash='dash', text=f"Med({val} | {rank}%)")


    if plot_flags.get("pc_line", 1):
        if pc_line is not None:
            try:
                percentile_val = get_percentile(sub_series, pc_line)
                pc_line = float(pc_line)
                add_vline(fig, percentile_val, color='#483D8B', dash='dash', text=f"Val ({percentile_val} | {pc_line}%)")
            except (ValueError, TypeError):
                # ignore bad inputs (non-numeric)
                pass

    if plot_flags.get("val_line", 1):
        if val_line is not None:
            try:
                val = float(val_line)
                # Clamp to series range
                if val < sub_series.min():
                    val = sub_series.min()
                elif val > sub_series.max():
                    val = sub_series.max()

                # Rank & rounding
                rank = round(get_rank(sub_series, val))
                val = round(val, 1)

                add_vline(fig, val, color='#005BBB', dash='dash', text=f"Val ({val} | {rank}%)")
            except (ValueError, TypeError):
                # ignore bad inputs (non-numeric)
                pass

    if plot_flags.get("Latest", 1):
        latest_val = round(latest_val, 2)
        rank = get_rank(sub_series, latest_val)
        if not np.isnan(rank):
            add_vline(fig, latest_val, color='red', width=3, text=f"Latest({latest_val} | {round(rank)}%)")

    #fig.show(config={"scrollZoom": True})
    return fig


def warning_plot_copy(warning):
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