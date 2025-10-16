from dash import dcc, html
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import numpy as np

from str_cal import  rolling_bounds_filter,process_help_calculation, get_rank

########################################### tab2_2 buttons #################################################
default_2_2_2_3 = {
    "btn-ease_hike": True,   # e.g. default ON
    "btn-nth_out": False,
    "btn-mid_out": False,
    "btn-1sts12": False,
    "btn-nths12": False,
    "btn-12ths12": False,
    "btn-nthl6": False,
    "btn-effr": False,
    "btn-2yr": False,
    "btn-5yr": False,
    "btn-10yr": False,
    "btn-2y10y":False,

    "btn-ease_hike_3twin": True,   # e.g. default ON
    "btn-nth_out_3twin": False,
    "btn-mid_out_3twin": False,
    "btn-1sts12_3twin": False,
    "btn-nths12_3twin": False,
    "btn-12ths12_3twin": False,
    "btn-nthl6_3twin": False,
    "btn-effr_3twin": False,
    "btn-2yr_3twin": False,
    "btn-5yr_3twin": False,
    "btn-10yr_3twin": False,
    "btn-2y10y_3twin":False,
}

tab_2_2_2_3_button_ids = list(default_2_2_2_3.keys())


def get_button_class(is_active: bool) -> str:
    base = "tab-button me-2"
    return base + " selected" if is_active else base

def build_button(label, id, active=False):
    return dbc.Button(
        label,
        id=id,
        className= get_button_class(active), 
        n_clicks=0
    )


def create_tab2_view():
    view= dcc.Tab(
        label='Chart',
        value='tab2',
        style={
            "height": "42px", "borderRadius": "8px 8px 0 0", "padding": "8px 16px",
            "marginRight": "4px", "backgroundColor": "#2b2e35", "color": "#c0c4cc",
            "fontWeight": "500", "border": "1px solid #3a3f4b", "borderBottom": "none",
            "transition": "background-color 0.3s, color 0.3s"
        },
        selected_style={
            "height": "45px", "borderRadius": "8px 8px 0 0", "padding": "8px 16px",
            "backgroundColor": "#1f2128", "color": "#ffffff", "fontWeight": "600",
            "border": "1px solid #5e636e", "borderBottom": "none",
            "boxShadow": "0px -2px 6px rgba(0, 0, 0, 0.4)"
        },
        children=[
            html.Div([
                # --- ROW 1: Main Chart (The Reference) ---
                # Structure: dbc.Col -> dcc.Loading -> dcc.Graph
                dbc.Row([
                    dbc.Col(
                        dcc.Loading(
                            id="loading-chart",
                            type="circle",
                            children=dcc.Graph(
                                id='chart-plot',
                                config={'scrollZoom': True, 'displayModeBar': False}
                            )
                        ),
                        className="border p-2 my-2 rounded"
                    )
                ], className="mb-3"),

                # --- ROW 2: Secondary Chart (Corrected) ---
                # <<< CHANGE: The structure is now identical to Row 1
                # Structure: dbc.Col -> [Buttons_Div, dcc.Loading]
                dcc.Store(id="tab_2_2_2_3_toggle-store", data=default_2_2_2_3),    
                dbc.Row([
                    dbc.Col(
                        # The children are now a list containing the buttons and the graph
                        children=[
                            # Item 1: The buttons
                            
                            html.Div([
                                build_button("Sum of eases/ hikes", id="btn-ease_hike", active=default_2_2_2_3["btn-ease_hike"]),
                                build_button("nth Out", id="btn-nth_out", active=default_2_2_2_3["btn-nth_out"]),
                                build_button("Mid Out", id="btn-mid_out",active=default_2_2_2_3["btn-mid_out"]),
                                build_button("1st S12", id="btn-1sts12",active=default_2_2_2_3["btn-1sts12"]),
                                build_button("nth S12", id="btn-nths12",active=default_2_2_2_3["btn-nths12"]),
                                build_button("12th S12", id="btn-12ths12",active=default_2_2_2_3["btn-12ths12"]),
                                build_button("nth L6", id="btn-nthl6",active=default_2_2_2_3["btn-nthl6"]),
                                build_button("EFFR", id="btn-effr",active=default_2_2_2_3["btn-effr"]),
                                build_button("2 Yr", id="btn-2yr",active=default_2_2_2_3["btn-2yr"]),
                                build_button("5 Yr", id="btn-5yr",active=default_2_2_2_3["btn-5yr"]),
                                build_button("10 Yr", id="btn-10yr",active=default_2_2_2_3["btn-10yr"]), #
                                build_button("2y10y", id="btn-2y10y",active=default_2_2_2_3["btn-2y10y"]),
                            ],
                            style={
                                'display': 'flex',
                                'gap': '0.5rem',
                                'justifyContent': 'center',
                                'flexWrap': 'wrap',
                                'marginBottom': '1rem'
                            }),

                            # Item 2: The graph
                            dcc.Loading(
                                id="loading-sum-eases",
                                type="circle",
                                # Use flex-grow to make the graph fill the remaining vertical space
                                children=dcc.Graph(
                                    id='sum-of-eases-plot',
                                    config={'scrollZoom': True, 'displayModeBar': False},
                                    style={'height': '100%'}
                                ),
                                style={'flex-grow': 1}
                            )
                        ],
                        # Styles are applied directly to the dbc.Col
                        className="border p-2 my-2 rounded",
                        # style={
                        #     'height': '500px',
                        #     'display': 'flex',
                        #     'flexDirection': 'column'
                        # }
                    )
                ]),

                # --- ROW 3: Third Chart ---
                # Structure: dbc.Col -> dcc.Loading -> dcc.Graph
                dbc.Row([
                    dbc.Col(
                        # The children are now a list containing the buttons and the graph
                        children=[
                            # Item 1: The buttons
                            html.Div([
                                build_button("Sum of eases/ hikes", id="btn-ease_hike_3twin", active=default_2_2_2_3["btn-ease_hike_3twin"]),
                                build_button("nth Out", id="btn-nth_out_3twin", active=default_2_2_2_3["btn-nth_out_3twin"]),
                                build_button("Mid Out", id="btn-mid_out_3twin",active=default_2_2_2_3["btn-mid_out_3twin"]),
                                build_button("1st S12", id="btn-1sts12_3twin",active=default_2_2_2_3["btn-1sts12_3twin"]),
                                build_button("nth S12", id="btn-nths12_3twin",active=default_2_2_2_3["btn-nths12_3twin"]),
                                build_button("12th S12", id="btn-12ths12_3twin",active=default_2_2_2_3["btn-12ths12_3twin"]),
                                build_button("nth L6", id="btn-nthl6_3twin",active=default_2_2_2_3["btn-nthl6_3twin"]),
                                build_button("EFFR", id="btn-effr_3twin",active=default_2_2_2_3["btn-effr_3twin"]),
                                build_button("2 Yr", id="btn-2yr_3twin",active=default_2_2_2_3["btn-2yr_3twin"]),
                                build_button("5 Yr", id="btn-5yr_3twin",active=default_2_2_2_3["btn-5yr_3twin"]),
                                build_button("10 Yr", id="btn-10yr_3twin",active=default_2_2_2_3["btn-10yr_3twin"]),
                                build_button("2y10y", id="btn-2y10y_3twin",active=default_2_2_2_3["btn-2y10y_3twin"]),
                            ],
                            style={
                                'display': 'flex',
                                'gap': '0.5rem',
                                'justifyContent': 'center',
                                'flexWrap': 'wrap',
                                'marginBottom': '1rem'
                            }),

                            # Item 2: The graph
                            dcc.Loading(
                                id="loading-scatters",
                                type="circle",
                                # Use flex-grow to make the graph fill the remaining vertical space
                                children=dcc.Graph(
                                    id='scatter_plot_2_3',
                                    config={'scrollZoom': True, 'displayModeBar': False},
                                    style={'height': '100%'}
                                ),
                                style={'flex-grow': 1}
                            )
                        ],
                        # Styles are applied directly to the dbc.Col
                        className="border p-2 my-2 rounded",
                        # style={
                        #     'height': '500px',
                        #     'display': 'flex',
                        #     'flexDirection': 'column'
                        # }
                    )
                ]),

            ], style={'padding': '16px'})
        ]
    )
    return view




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

def cal_sum_of_eases_hikes(out_df, comdty, lookback_prd, DEFAULT_WINDOW, DEFAULT_OUTLIER_K ):
    S3_df, comdty = process_help_calculation(comdty, out_df, "S3", lookback_prd, 15,DEFAULT_WINDOW, DEFAULT_OUTLIER_K )
    sum_of_eases_hikes_series = compute_conditional_sum(S3_df,8)
    #print(len(sum_of_eases_hikes_series))
    sum_of_eases_hikes_series= sum_of_eases_hikes_series.head(lookback_prd)
    index = out_df.index[:lookback_prd]
    return pd.Series(sum_of_eases_hikes_series, index=index)

def cal_sum_of_same_sign_meets(out_df, comdty, lookback_prd, DEFAULT_WINDOW, DEFAULT_OUTLIER_K ):
    Out_df, comdty = process_help_calculation(comdty, out_df, "Out", lookback_prd, 20, DEFAULT_WINDOW, DEFAULT_OUTLIER_K )
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
    if corr is not None:
        if corr['pearson'] is not None:
            fig.add_annotation(
                x=latest_x,
                y=y0,
                text=f"Corr: ({round(corr['pearson'],1)})",
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




def Out_tab2_2(raw_df,comdty, str_number, lookback_prd, DEFAULT_WINDOW, DEFAULT_OUTLIER_K):
    if raw_df.empty:
        return pd.Series()

    max_cols = raw_df.shape[1]
    max_rows = raw_df.shape[0]
    actual_lookback = min(lookback_prd, max_rows)
    if str_number > max_cols:
        str_number = max_cols
    series = raw_df.iloc[:actual_lookback, str_number - 1].copy()
    return rolling_bounds_filter(series, window= DEFAULT_WINDOW, k= DEFAULT_OUTLIER_K)

def S12_tab2_2(out_df, n, lookback_prd, DEFAULT_WINDOW,DEFAULT_OUTLIER_K ):
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

def L6_tab2_2(out_df, n, lookback_prd, DEFAULT_WINDOW,DEFAULT_OUTLIER_K ):
    if n + 2 >= out_df.shape[1]:
        print( "n+2 column index exceeds DataFrame width")
        return pd.series()
    series = (out_df.iloc[:lookback_prd,n-1] - 2* out_df.iloc[:lookback_prd, n+1]+ out_df.iloc[:lookback_prd, n+3])*100
    #print(series.head(), len(series))
    series= rolling_bounds_filter(series, window= DEFAULT_WINDOW, k= DEFAULT_OUTLIER_K)
    return series


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
        return {"pearson":None, "mean_rolling_correlation": None,"distance_correlation": None}
    #print(f"Input series must have the same length {len(series1)}, {len(series2)}")
    if len(series1) != len(series2):
        print(f"Input series must have the same length {len(series1)}, {len(series2)}")
        return {"pearson":None, "mean_rolling_correlation": None,"distance_correlation": None}

    if len(series1) < rolling_window:
        print(f"Input series length ({len(series1)}) cannot be less than the rolling window size ({rolling_window}).")
        return {"pearson":None,"mean_rolling_correlation": None,"distance_correlation": None}
    
    series1 = pd.to_numeric(series1, errors="coerce")
    series2 = pd.to_numeric(series2, errors="coerce")
    series1.replace([np.inf, -np.inf], np.nan, inplace=True)
    series2.replace([np.inf, -np.inf], np.nan, inplace=True)
    # This creates a new series where each point is the correlation of the preceding 'window' data points.
    rolling_corr = series1.rolling(window=rolling_window).corr(series2)
    # The first (window - 1) values will be NaN, so we drop them before calculating the mean.
    mean_rolling_corr = rolling_corr.dropna().mean()
    #pearson_correlation
    pearson = series1.corr(series2)


    # # --- 3. Distance Correlation (dCor) ---
    # # dCor is powerful because it is zero if and only if the series are truly independent.
    # # It captures non-linear and non-monotonic relationships that standard correlation would miss.
    # dist_corr = dcor.distance_correlation(series1.values, series2.values)
    dist_corr=0

    return {
        'pearson': pearson, 
        'mean_rolling_correlation': mean_rolling_corr,
        'distance_correlation': dist_corr,
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
    if series_Y is None:
        return
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