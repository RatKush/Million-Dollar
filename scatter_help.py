import pandas as pd
import numpy as np
from scipy.stats import gaussian_kde, mode
import plotly.graph_objects as go
#from main import str_df

""""----------------------------------intact---------------------------------------"""
from data_loader import load_data, fill_missing_values
from str_cal import get_ratio, calculate_str, remove_outliers

str_name= "D6"  
out_curve_df = fill_missing_values(load_data())                                              ## 2. input ##
str_df = calculate_str(out_curve_df, get_ratio(str_name))
str_df = remove_outliers(str_df,lower_quantile=0.01, upper_quantile=0.99)

curve_length= 18                                        ## 1. trim upto req str 
str_df= str_df.iloc[:,:curve_length]  
#plot_title= str_name+ "("+ str_number+ ") @"+ lookback_prd+ "d"                          
""""  ----------------------------intact--------------------------------------------"""

def init_plot(title):
    """Initialize plot with consistent layout and styling."""
    fig = go.Figure()
    fig.update_layout(
        xaxis_title='Value',
        yaxis_title='Density',
        title=dict(text=title, x=0.5, y=0.99, xanchor="center"),  # Centered title
        #hovermode="x unified",  # Shared hover mode along x-axis
        legend=dict(
            x=0.5, y=1,
            orientation="h",  # Horizontal legend at top center
            xanchor="center",
            yanchor="bottom"
        ),
        margin=dict(t=60),  # Top margin to leave room for title
        dragmode="pan"  # Enable panning instead of zooming
        
    )

    return fig  # Return initialized figure



def extract_series(str_df= str_df ,str_number= 8, lookback_prd=250):
    series= str_df.iloc[:, str_number-1]  # n-th column (0-based index)
    series= series.iloc[:lookback_prd]
    #Make sure your index is datetime type
    series.index = pd.to_datetime(series.index)
    series = series.dropna()
    return series

def small_window_stats(str_series, small_window=21, std_multi=1):
    cur_win_mean= str_series.head(small_window).mean()
    cur_win_std= str_series.head(small_window).std()
    cur_win_max= str_series.head(small_window).max()
    cur_win_min= str_series.head(small_window).min()
    cur_win_bband= {cur_win_mean-std_multi*cur_win_std, cur_win_mean+std_multi*cur_win_std}
    window= { "mean":cur_win_mean, "std":cur_win_std, "max":cur_win_max, "min":cur_win_min, "bb":cur_win_bband}
    return window   

def compute_stats(str_series):
    skewness= str_series.skew().round(1)
    excess_kurt= str_series.kurt().round(1)
    zscore = ((str_series.iloc[0] - str_series.mean()) / str_series.std()).round(1)
    mean= np.mean(str_series)
    median= np.median(str_series)
    mod= mode(str_series)[0]
    std= np.std(str_series).round(1)
    stats= {"skew": skewness, "kurt": excess_kurt, "z": zscore, "mean": mean, "med":median, "mod":mod, "std":std}
    return stats

def get_percentile(str_series, pc):
    return np.percentile(str_series, pc).round(1)

#Visualize kernal density estimation/ distribution:  # KDE line
def plot_kde(fig, series):
    series = pd.to_numeric(series, errors='coerce')
    series = series[~np.isnan(series)] 
    if len(series) >= 2 and not np.isnan(series).all():
        kde = gaussian_kde(series)
        x_vals = np.linspace(series.min(), series.max(), 300)
        kde_vals = kde(x_vals)
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=kde_vals,
            #legend= False,
            mode='lines',
            name='KDE',
            line=dict(color='royalblue', width=3),
            showlegend=False,
            hovertemplate='val: %{x:.1f}' #<br>Y: %{y:.1f}<extra></extra>'
        ))
        return fig

    else:
    print("Not enough data for KDE. Skipping...")
    return fig  # or handle it differently   



# --- Function to add a vertical line ---
# def add_vline(fig, x, color='black', dash='solid', width=2, text=None, position="top right", opacity=1.0):
#     fig.add_vline(
#         x=x,
#         line=dict(color=color, dash=dash, width=width),
#         annotation_text=text,
#         annotation_position=position,
#         opacity=opacity
#     )

def add_vline(fig, x, color='black', dash='solid', width=2, text=None, position="top right", opacity=1.0, showlegend=True, zorder=1):
    # Add a vertical line using a scatter trace (so it can appear in legend)
    # Collect all y-data from existing traces
    y_vals = []
    for trace in fig.data:
        if 'y' in trace:
            y_vals.extend(trace.y)

    if not y_vals:
        y_min, y_max = 0, 1
    else:
        y_min = np.nanmin(y_vals)
        y_max = np.nanmax(y_vals)


    fig.add_trace(go.Scatter(
        x=[x, x],
        y=[y_min, y_max],
        mode='lines',
        line=dict(color=color, dash=dash, width=width),
        name=text if showlegend else '',
        showlegend=showlegend,
        hoverinfo='skip',
        opacity=opacity
        #zorder= zorder
    ))

    return fig

def add_band_mask(fig, lower_pct, upper_pct, kde_trace_name, name): #inputs are values here
    kde_trace = next(
        (t for t in fig.data if isinstance(t, go.Scatter) and t.name == kde_trace_name),
        None
    )
    if kde_trace is None:
        raise ValueError(f"No trace named '{kde_trace_name}' found in the figure.")

    # Step 2: Extract x and y values from the trace
    x_vals = np.array(kde_trace.x)
    kde_vals = np.array(kde_trace.y)

    band_mask = (x_vals >= lower_pct) & (x_vals <= upper_pct)
    x_band = x_vals[band_mask]
    y_band = kde_vals[band_mask]

    # Percentile band as filled area under KDE
    fig.add_trace(go.Scatter(
        x=np.concatenate([x_band, x_band[::-1]]),  # x forward then backward
        y=np.concatenate([y_band, np.zeros_like(y_band)]),  # y KDE then zero baseline
        fill='toself',
        fillcolor='rgba(137, 207, 240, 0.3)',  # transparent blue
        line=dict(color='rgba(255,255,255,0)'),  # no border line
        hoverinfo='skip',
        showlegend=True,
        name= name #'5-95% Percentile Band'
    ))
    return fig


def get_rank(series, val):
    series = series.dropna().values
    if len(series) == 0:
        return np.nan

    rank = (np.sum(series < val) + 0.5 * np.sum(series == val)) / len(series)
    return rank * 100

# #percentiles# Percentile bands
# for i, p in enumerate(percentiles):
#     add_vline(fig, p, color='orange', dash='dot', text=f"{[5,25,50,75,95][i]}%", opacity=0.5)





















"""
Skewness: distribution leans to the right or left.
Kurtosis: how fat the tails of a distribution are. Fat or skinny
Skew > 0 → distribution is right-skewed (long right tail; more small values, a few high outliers). 
Positive skew: more likely to observe small spreads, but large spikes possible.
#Skew < 0 → distribution is left-skewed (long left tail; more large values, a few low outliers).
Negative skew: more likely to observe larger spreads, but sharp drops are possible.
#Skew ≈ 0 → approximately symmetric (like normal distribution).

Excess kurtosis > 0 → heavy tails (risk of outliers)  skinny| tall
Excess kurtosis < 0 → light tails (less extreme risk) fat| short
"""
