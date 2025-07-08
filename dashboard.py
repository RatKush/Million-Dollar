# A Dash app to explore structure curve data: Curve view, chart and KDE analysis

import os
import pandas as pd
import dash
from dash import dcc, html
from dash import Input, Output, State, ctx
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# Custom modules
from str_cal import process_structure, extract_comdty,process_help_calculation, index 
from curve_plotter import plot_single_structure
from curve_plotter import generate_curve_plot, cal_sum_of_eases_hikes
from kde_help import plot_main_kde, classify_cycle, plotted

# ------------------------------------------------
# UTILITY: Read all available Excel files in local directory
# ------------------------------------------------
def get_excel_files(path='.'):
    return [f for f in os.listdir(path) if f.lower().endswith(('.xlsx', '.xlsm'))]


excel_files = get_excel_files()
filename_options = [{'label': f, 'value': f} for f in excel_files]

# ------------------------------------------------remove_outliers
# DASH APP INITIALIZATION
# ------------------------------------------------
app = dash.Dash(__name__, assets_folder='assets',external_stylesheets=[dbc.themes.CYBORG])
app.title = "Million Dollar"
app.config.suppress_callback_exceptions = True# for live
# ##############################shared control panel for all 4 kde plot cntrol tab3---- tab6################################
def get_kde_controls():
    return html.Div([
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
                        dcc.Input(id="hike-threshold-input", type="number", value=50, step=10, debounce=True,
                                className="form-control form-control-sm", style={"width": "32%"})
                    ], className="d-flex justify-content-between mb-2"),

                    html.Div([
                        html.Label("Ease Thrshld", className="form-label", style={"width": "68%", "marginBottom": 0}),
                        dcc.Input(id="ease-threshold-input", type="number", value=-50, step=10, debounce=True,
                                className="form-control form-control-sm", style={"width": "32%"})
                    ], className="d-flex justify-content-between mb-1")

                ], style={"padding": "12px 10px 10px 10px"})

            ], style={
                "border": "1px solid #3a3f4b",
                "borderRadius": "6px",
                "backgroundColor": "#2b2e35",
                "margin": "10px 0 18px 0"
            }),


        dbc.Checklist(
            id='kde-flags-shared',
            options=[
                {"label": "Latest", "value": "Latest"},
                {"label": "Band 68%", "value": "band68"},
                {"label": "Band 95%", "value": "band95"},
                {"label": "Local Mean", "value": "local_mean"},
                {"label": "Local XN", "value": "local_xn"},
                {"label": "Local Mean ± 1σ", "value": "local_bb"},
                {"label": "Mean", "value": "mean"},
                {"label": "Median", "value": "med"},
                {"label": "Mode", "value": "mod"},
                {"label": "% Line", "value": "pc_line"},
                {"label": "Val Line", "value": "val_line"},
                {"label": "± 1σ", "value": "bb1"},
                {"label": "± 2σ", "value": "bb2"},
            ],
            value=["Latest", "local_mean", "med", "band68", "band95"],
            switch=True,
            className="px-3 mb-3"
        ),

        html.Div([
            html.Label("Local Win", className="form-label", style={"width": "68%"}),
            dcc.Input(id="kde-local-win-shared", type="number", value=15, min=1, step=2, debounce=True, className="form-control form-control-sm", style={"width": "32%"})
        ], className=" px-3 mb-2 hidden-row", id="kde-local-row"),

        html.Div([
            html.Label("Val Line", className="form-label", style={"width": "68%"}),
            dcc.Input(id="kde-val-line-shared", type="number", value=0, debounce=True, className="form-control form-control-sm", style={"width": "32%"})
        ], className=" px-3 mb-2 hidden-row", id="kde-val-row"),

        html.Div([
            html.Label("% Line", className="form-label", style={"width": "68%"}),
            dcc.Input(id="kde-pc-line-shared", type="number", value=95, min=0, max=100, step=5, debounce=True, className="form-control form-control-sm", style={"width": "32%"})
        ], className=" px-3 mb-2 hidden-row", id="kde-pc-row")

    ], className="control-panel-1")


  # Full width inside 2/12 container



dcc.Store(id='kde-shared-store', storage_type='session',
    data={
        'flags': ["Latest", "local_mean", "band68","band95" ],
        'local_win': 10,
        'val_line': 0,
        'pc_line': 95
    })
#wrapper for easy styling and clarity needed to add in layout 
dbc.Container(
    id="kde-flags-shared-wrapper",
    children=get_kde_controls(),
    className="kde-floating-panel-css",
    style={"display": "none"}  # Hidden by default
)


##################################################### app layout #############################################################
# ------------------------------------------------
# DASH LAYOUT
# -----------------------------------------------
# UI layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Label("Filename", style={"color": "#c0c4cc", "fontWeight": "500",  "fontSize": "14px",   "marginBottom": "4px" }),
            dcc.Dropdown(
                id='filename',
                options=filename_options,
                value="SR3.xlsx" if "SR3.xlsx" in excel_files else excel_files[0] if excel_files else None,
                clearable=False,
                className='form-control'
            )
        ]),
        dbc.Col([
            html.Label("Comdty",style={"color": "#c0c4cc", "fontWeight": "500",  "fontSize": "14px",   "marginBottom": "4px" }),
            dcc.Loading(
                dcc.Input(id='comdty', type='text', value='', disabled=True, className='form-control'),
            type= 'circle'
            )
        ]),
        dbc.Col([
            html.Label("Structure", style={"color": "#c0c4cc", "fontWeight": "500",  "fontSize": "14px",   "marginBottom": "4px" }),
            dcc.Dropdown(
                id='str_name',
                options=index,
                value="L6",
                clearable=False,
                className='form-control'
            )
        ]),
        dbc.Col([
            html.Label("Curve Length",style={"color": "#c0c4cc", "fontWeight": "500",  "fontSize": "14px",   "marginBottom": "4px" }),
            dcc.Input(id='curve_length', type='number', value=15, min= 5,  className='form-control')
        ]),
        dbc.Col([
            html.Label("Str Number", style={"color": "#c0c4cc", "fontWeight": "500",  "fontSize": "14px",   "marginBottom": "4px" }),
            dcc.Input(id='str_number', type='number', value=8, min=1, className='form-control')
        ]),
        dbc.Col([
            html.Label("Lookback Period", style={"color": "#c0c4cc", "fontWeight": "500",  "fontSize": "14px",   "marginBottom": "4px" }),
            dcc.Input(id='lookback_prd', type='number', value=250, min=10, step=10, className='form-control')
        ]),
        dbc.Col([
            html.Label(" "),
            dbc.Button("Load", id='load-btn', color='primary', className='mt-4')
        ])
    ], className='mb-4'),


####################### kde -control for tab3, tab4, tab5, tab6--- needto declare beffore tabs declation#######################
    dcc.Store(id='kde-shared-store', storage_type='session',
    data={
        'flags': ["Latest", "local_mean", "band68","band95" ],
        'local_win': 10,
        'val_line': 0,
        'pc_line': 95
    }),
    #wrapper for easy styling and clarity 
    dbc.Container(
        id="kde-flags-shared-wrapper",
        children=get_kde_controls(),
        className="my-2",
        style={"display": "none"}  # Hidden by default
    ),

  
####################################################################### tab 1 ###################################################
    dcc.Tabs(id="tabs", value='tab1', children=[
        dcc.Tab(label='Curve View', value='tab1',
        style={"height": "42px","borderRadius": "8px 8px 0 0","padding": "8px 16px","marginRight": "4px","backgroundColor": "#2b2e35","color":  "#c0c4cc","fontWeight": "500","border": "1px solid #3a3f4b","borderBottom": "none","transition": "background-color 0.3s, color 0.3s"
        },
        selected_style={"height": "45px","borderRadius": "8px 8px 0 0","padding": "8px 16px","backgroundColor": "#1f2128","color": "#ffffff","fontWeight": "600","border": "1px solid #5e636e","borderBottom": "none","boxShadow": "0px -2px 6px rgba(0, 0, 0, 0.4)"
        },
        children=[
            dbc.Row([
                dbc.Col(dcc.Loading(
                    id="loading-curve",
                    type="circle",
                    children=html.Div(dcc.Graph(id='curve-plot', config={'scrollZoom': True, 'displayModeBar': False}),className="border p-2 my-2 rounded")), width=10),
                dbc.Col([
                    html.H5("Plot Controls", style={"color":"#c0c4cc","textAlign": "center", "padding": "8px 16px","backgroundColor": "#2b2e35","fontWeight": "500","fontSize": "16px","border": "1px solid #3a3f4b",  "borderTopLeftRadius": "8px",  "borderTopRightRadius": "8px", "margin": "0"},
                    ),
                    dbc.Checklist(
                        id='plot-flags',
                        options=[
                            {"label": "Latest", "value": "Latest"},
                            {"label": "Settle", "value": "Settle"},
                            {"label": "Date1", "value": "Date1"},
                            {"label": "Date2", "value": "Date2"},
                            {"label": "Moving Average", "value": "MA"},
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
                            dbc.Col(dbc.Label("Local Win"), width=6),
                            dbc.Col(dbc.Input(id="win-local", type="number", value=20, min=1, step=5, debounce=True, persistence=False), width=6)
                        ], id="win-local-row", className="mb-2", style={"display": "none"}),

                        dbc.Row([
                            dbc.Col(dbc.Label("Settle Offset"), width=6),
                            dbc.Col(dbc.Input(id="Settle_days-input", type="number", value=10, min=1, step=5, debounce=True, persistence=False), width=6)
                        ], id="settle-row", className="mb-2", style={"display": "none"}),

                        dbc.Row([
                            dbc.Col(dbc.Label("Date 1"), width=4),
                            dbc.Col(dbc.Input(id="date1-input", type="date", value="2025-06-05", step=1, placeholder="YYYY-MM-DD", debounce=True, persistence=False), width=8)
                        ], id="date1-row", className="mb-2", style={"display": "none"}),

                        dbc.Row([
                            dbc.Col(dbc.Label("Date 2"), width=4),
                            dbc.Col(dbc.Input(id="date2-input", type="date", value="2024-09-25", step=1, placeholder="YYYY-MM-DD", debounce=True, persistence=False), width=8)
                        ], id="date2-row", className="mb-2", style={"display": "none"}),

                        dbc.Row([
                            dbc.Col(dbc.Label("Quantile"), width=3),
                            dbc.Col(dbc.Input(id="quantile-input", type="number", value=95, min=0, max=100, step=5, debounce=True, persistence=False), width=9)
                        ], id="quantile-row", className="mb-2", style={"display": "none"}),

                        dbc.Row([
                            dbc.Col(dbc.Label("BB Std Dev"), width=6),
                            dbc.Col(dbc.Input(id="bb-std-input", type="number", value=1, min=1, step=1, debounce=True, persistence=False), width=6)
                        ], id="bb-std-row", className="mb-2", style={"display": "none"}),
                    ], gap=1)
                ], width=2)
            ])
        ]),
###################################################  tab 2 ##############################################################################
    dcc.Tab(label='Chart', value='tab2',
    style={"height": "42px","borderRadius": "8px 8px 0 0","padding": "8px 16px","marginRight": "4px","backgroundColor": "#2b2e35","color":  "#c0c4cc","fontWeight": "500","border": "1px solid #3a3f4b","borderBottom": "none","transition": "background-color 0.3s, color 0.3s"
        },
    selected_style={"height": "45px","borderRadius": "8px 8px 0 0","padding": "8px 16px","backgroundColor": "#1f2128","color": "#ffffff","fontWeight": "600","border": "1px solid #5e636e","borderBottom": "none","boxShadow": "0px -2px 6px rgba(0, 0, 0, 0.4)"
        },
    children=[
        dbc.Row([
            dbc.Col(dcc.Loading(
                id="loading-chart",
                type="circle",
                children=html.Div([
                    dcc.Graph(id='chart-plot', config={'scrollZoom': True, 'displayModeBar': False}),
                ],className="border p-2 my-2 rounded")
            ), width=12)
        ]),
        dbc.Row([
            dbc.Col(dcc.Loading(
                id="loading-sum-eases",
                type="circle",
                children=html.Div([
                    dcc.Graph(id='sum-of-eases-plot', config={'scrollZoom': True, 'displayModeBar': False}),
                ],className="border p-2 my-2 rounded")
            ), width=12)
        ]),
        dbc.Row([
            dbc.Col(dcc.Loading(
                id="loading-effr-rate",
                type="circle",
                children=html.Div([
                    dcc.Graph(id='effr-plot', config={'scrollZoom': True, 'displayModeBar': False}),
                ],className="border p-2 my-2 rounded")
            ), width=12)
        ]),
    ]),
######################################################## tab3 #############################################################
    


    dcc.Tab(label='KDE', value='tab3',
    style={"height": "42px","borderRadius": "8px 8px 0 0","padding": "8px 16px","marginRight": "4px","backgroundColor": "#2b2e35","color":  "#c0c4cc","fontWeight": "500","border": "1px solid #3a3f4b","borderBottom": "none","transition": "background-color 0.3s, color 0.3s"
        },
    selected_style={"height": "45px","borderRadius": "8px 8px 0 0","padding": "8px 16px","backgroundColor": "#1f2128","color": "#ffffff","fontWeight": "600","border": "1px solid #5e636e","borderBottom": "none","boxShadow": "0px -2px 6px rgba(0, 0, 0, 0.4)"
        },
    children=[
        html.Div([  #####css-for-control panel
            dbc.Row([
                dbc.Col(dcc.Loading(
                    id="loading-kde",
                    type="circle", 
                    children=html.Div(dcc.Graph(id='kde-plot', config={'scrollZoom': True, 'displayModeBar': False}),className="border p-2 my-2 rounded")
                ), width=10),
            ])
        ],style={"position": "relative"})##########css-for-control panel
    ]), 

################################################ tab 4 ################################################################
dcc.Tab(label='KDE (Hike Cycle)', value='tab4',
    style={"height": "42px","borderRadius": "8px 8px 0 0","padding": "8px 16px","marginRight": "4px","backgroundColor": "#2b2e35","color":  "#c0c4cc","fontWeight": "500","border": "1px solid #3a3f4b","borderBottom": "none","transition": "background-color 0.3s, color 0.3s"
        },
    selected_style={"height": "45px","borderRadius": "8px 8px 0 0","padding": "8px 16px","backgroundColor": "#1f2128","color": "#ffffff","fontWeight": "600","border": "1px solid #5e636e","borderBottom": "none","boxShadow": "0px -2px 6px rgba(0, 0, 0, 0.4)"
        },
    children=[
        html.Div([  #####css-for-control panel
            dbc.Row([
                dbc.Col(dcc.Loading(
                    id="loading-hike-kde",
                    type="circle",
                    children=html.Div(dcc.Graph(id='hike-kde-plot', config={'scrollZoom': True, 'displayModeBar': False}),className="border p-2 my-2 rounded")
                ), width=10),
            ])
        ],style={"position": "relative"}) ##########css-for-control panel
    ]),

###################################################### tab 5 ###################################################
    dcc.Tab(label='KDE (Ease Cycle)', value='tab5',
    style={"height": "42px","borderRadius": "8px 8px 0 0","padding": "8px 16px","marginRight": "4px","backgroundColor": "#2b2e35","color":  "#c0c4cc","fontWeight": "500","border": "1px solid #3a3f4b","borderBottom": "none","transition": "background-color 0.3s, color 0.3s"
        },
    selected_style={"height": "45px","borderRadius": "8px 8px 0 0","padding": "8px 16px","backgroundColor": "#1f2128","color": "#ffffff","fontWeight": "600","border": "1px solid #5e636e","borderBottom": "none","boxShadow": "0px -2px 6px rgba(0, 0, 0, 0.4)"
        },
    children=[
        html.Div([  #####css-for-control panel
            dbc.Row([
                dbc.Col(dcc.Loading(
                    id="ease-loading-kde",
                    type="circle",
                    children=html.Div(dcc.Graph(id='ease-kde-plot', config={'scrollZoom': True, 'displayModeBar': False}),className="border p-2 my-2 rounded")
                ), width=10),
            ])
        ],style={"position": "relative"}) ##########css-for-control panel
    ]),

###################################################### tab 6 ####################################################
    dcc.Tab(label='KDE (Side Ways)', value='tab6',
    style={"height": "42px","borderRadius": "8px 8px 0 0","padding": "8px 16px","marginRight": "4px","backgroundColor": "#2b2e35","color":  "#c0c4cc","fontWeight": "500","border": "1px solid #3a3f4b","borderBottom": "none","transition": "background-color 0.3s, color 0.3s"
        },
    selected_style={"height": "45px","borderRadius": "8px 8px 0 0","padding": "8px 16px","backgroundColor": "#1f2128","color": "#ffffff","fontWeight": "600","border": "1px solid #5e636e","borderBottom": "none","boxShadow": "0px -2px 6px rgba(0, 0, 0, 0.4)"
        },
    
    children=[
        dbc.Row([
            dbc.Col(dcc.Loading(
                id="side-loading-kde",
                type="circle",
                children=html.Div(dcc.Graph(id='side-kde-plot', config={'scrollZoom': True, 'displayModeBar': False}),className="border p-2 my-2 rounded")
            ), width=10),
        ])
    ]),
############################################################# tab 7 ################################################################        
    dcc.Tab(label='Matrix Filter', value='tab7',
    style={"height": "42px","borderRadius": "8px 8px 0 0","padding": "8px 16px","marginRight": "4px","backgroundColor": "#2b2e35","color":  "#c0c4cc","fontWeight": "500","border": "1px solid #3a3f4b","borderBottom": "none","transition": "background-color 0.3s, color 0.3s"
        },
    selected_style={"height": "45px","borderRadius": "8px 8px 0 0","padding": "8px 16px","backgroundColor": "#1f2128","color": "#ffffff","fontWeight": "600","border": "1px solid #5e636e","borderBottom": "none","boxShadow": "0px -2px 6px rgba(0, 0, 0, 0.4)"
        },

    ),



################################################################# tab 8 ###################################################
    dcc.Tab(label='Snapshot', value='tab8',
    style={"height": "42px","borderRadius": "8px 8px 0 0","padding": "8px 16px","marginRight": "4px","backgroundColor": "#2b2e35","color":  "#c0c4cc","fontWeight": "500","border": "1px solid #3a3f4b","borderBottom": "none","transition": "background-color 0.3s, color 0.3s"
        },
    selected_style={"height": "45px","borderRadius": "8px 8px 0 0","padding": "8px 16px","backgroundColor": "#1f2128","color": "#ffffff","fontWeight": "600","border": "1px solid #5e636e","borderBottom": "none","boxShadow": "0px -2px 6px rgba(0, 0, 0, 0.4)"
        },

    ),
]),  # ← close Tabs here


    dcc.Store(id='stored-data', storage_type='local' ),#persistence=True
    dcc.Store(id='cycle-store',storage_type='local' )#persistence=True
    #html.Div(id='output-area', className='border p-3 my-2')

], fluid=True)  # ← close Container here

################################################################ #########################################################
# ---------------------------------------------------------------------------------------------------
# CALLBACK: Load & Process Structure Data tab 1
# ------------------------------------------------------------------------------------------------------
@app.callback(
    Output('stored-data', 'data'),
    Output('comdty', 'value'),
    Input('filename', 'value'),
    Input('str_name', 'value'),
    Input('curve_length', 'value'),
    Input('str_number', 'value'),
    Input('lookback_prd', 'value')
)
def store_data(filename, str_name, curve_length, str_number, lookback_prd):
    try:
        comdty = extract_comdty(filename)

        out_df, str_df, series, comdty, str_name, str_number = process_structure(
            filepath=filename,
            str_name=str_name,
            str_number=int(str_number),
            lookback_prd=int(lookback_prd),
            curve_length=int(curve_length)
        )
        return {
            "out_df": {
                "data": out_df.values.tolist(),
                "index": out_df.index.astype(str).tolist(),
                "columns": out_df.columns.tolist()
            },
            "str_df": {
                "data": str_df.values.tolist(),
                "index": str_df.index.astype(str).tolist(),
                "columns": str_df.columns.tolist()
            },
            "series": {
                "values": list(series),
                "index": series.index.astype(str).tolist()
            },
            "comdty": comdty,
            "str_name": str_name,
            "str_number": str_number,
            "lookback_prd": lookback_prd
        }, comdty
    except Exception:
        return {}, ""

# ------------------------------------------------------------------------------------------------------------------
# CALLBACK: Toggle Visibility of Curve Controls tab 1
# --------------------------------------------------------------------------------------------------------------------
@app.callback([
    Output("settle-row", "style"),
    Output("date1-row", "style"),
    Output("date2-row", "style"),
    Output("quantile-row", "style"),
    Output("bb-std-row", "style"),
    Output("win-local-row", "style")
], Input("plot-flags", "value"))
def toggle_input_visibility(active_flags):
    return [
        {"display": "block"} if "Settle" in active_flags else {"display": "none"},
        {"display": "block"} if "Date1" in active_flags else {"display": "none"},
        {"display": "block"} if "Date2" in active_flags else {"display": "none"},
        {"display": "block"} if "quant_ser" in active_flags else {"display": "none"},
        {"display": "block"} if "BB" in active_flags else {"display": "none"},
        {"display": "block"} if any(f in active_flags for f in ["MA", "MED", "BB", "quant_ser", "XN"]) else {"display": "none"}
    ]


# ------------------------------------------------
# CALLBACK: Curve Plot for Tab 1
# ------------------------------------------------
@app.callback(
    Output('curve-plot', 'figure'),
    Input('stored-data', 'data'),
    Input('plot-flags', 'value'),
    Input('Settle_days-input', 'value'),
    Input('date1-input', 'value'),
    Input('date2-input', 'value'),
    Input('win-local', 'value'),
    Input('quantile-input', 'value'),
    Input('bb-std-input', 'value'),
    prevent_initial_call=False
)
def update_curve_plot(stored, active_flags, Settle_days, date1, date2, win_local, quantile, bb_std):
    if not stored:
        return warning_plot("Series data not availbale (no stored data)")

    str_df = pd.DataFrame( 
        data=stored["str_df"]["data"],
        index=pd.to_datetime(stored["str_df"]["index"]),
        columns=stored["str_df"]["columns"]
    )

    plot_flags = {key: key in active_flags for key in ["Latest", "Settle", "Date1", "Date2", "MA", "MED", "quant_ser", "BB", "XN"]}
    #print(plot_flags["Date1"],date1, "d1", date2, "d2", plot_flags["Date2"])
    return generate_curve_plot(
        str_df=str_df,
        plot_title=f"{stored['comdty']}{stored['str_name']}",
        plot_flags=plot_flags,
        Settle=Settle_days if plot_flags["Settle"] else None,
        date1=date1 if plot_flags["Date1"] else None,
        date2=date2 if plot_flags["Date2"] else None,
        win_local=win_local,
        quantile=quantile if plot_flags["quant_ser"] else None,
        bb_std=bb_std if plot_flags["BB"] else None
    )

# ------------------------------------------------
# CALLBACK: Single Structure Plot (Tab 2)
# ------------------------------------------------
@app.callback(
    [Output('chart-plot', 'figure'),
    Output('sum-of-eases-plot', 'figure')],
    Input('stored-data', 'data'),
    prevent_initial_call=True
)
def update_chart_tab(stored):
    if not stored:
        return warning_plot("Series data not availbale (no stored data)")
    
    s = stored['series']
   
    series = pd.Series(data=s['values'], index=pd.to_datetime(s['index']))
    #print(series.head())
    str_name = f"{stored['comdty']}{stored['str_name']}({stored['str_number']})"
    comdty= stored["comdty"]
    out_df = pd.DataFrame( 
        data=stored["out_df"]["data"],
        index=pd.to_datetime(stored["out_df"]["index"]),
        columns=stored["out_df"]["columns"]
    )
    lookback_prd= stored["lookback_prd"]
    # sum of ease/ hike limited upto first 8 S3s
    #print(comdty)
    if comdty in {"VIX", "FVS", "meets", "SR1","SZI0", "VIX- VOXX" }:
        sum_of_ease_or_hikes= pd.Series(dtype='float64')
    else:
        sum_of_ease_or_hikes= cal_sum_of_eases_hikes(out_df, comdty, lookback_prd)
    return plot_single_structure(series, str_name),plot_single_structure(sum_of_ease_or_hikes, "sum of eases/ hikes")


# ---------------------------------------------------------------------------------------------------------
# CALLBACK:  shared KDE Input Toggle tab3 | tab4 | tab5 | tab6
# ------------------------------------------------------------------------------------------------------------

#rendering control panel in tab 3 to tab6
@app.callback(
    Output("kde-flags-shared-wrapper", "style"),
    Input("tabs", "value")
)
def toggle_kde_controls_visibility(active_tab):
    # Show only for Tab 3 to 6
    if active_tab in ['tab3', 'tab4', 'tab5', 'tab6']:
        return {"display": "block"}  # or use "flex" if you prefer
    return {"display": "none"}

#invisibility 
@app.callback(
    [
        Output("kde-val-row", "style"),
        Output("kde-pc-row", "style"),
        Output("kde-local-row", "style")
    ],
    [
        Input("kde-flags-shared", "value"),
        Input("tabs", "value")
    ],
    prevent_initial_call=True
)
def toggle_input_visibility_kdes(kde_flags, active_tab):
    return [
        {"display": "flex"} if "val_line" in kde_flags else {"display": "none"},
        {"display": "flex"} if "pc_line" in kde_flags else {"display": "none"},
        {"display": "flex"} if any(f in kde_flags for f in ["local_mean", "local_xn", "local_bb"]) else {"display": "none"}
    ]



# # --------------------------------------------------------------------------------------------
# # CALLBACK: KDE Plot (Tab 3)
# # ----------------------------------------------------------------------------------------------------
@app.callback(
    Output('kde-plot', 'figure'),
    Input('stored-data', 'data'),
    Input('kde-flags-shared', 'value'),
    Input('kde-local-win-shared', 'value'),
    Input('kde-val-line-shared', 'value'),
    Input('kde-pc-line-shared', 'value'),
    Input('tabs', 'value'), # Optional if tab switching logic is handled
    prevent_initial_call=False
)
def update_kde_plot_tab3(stored, kde_flags, local_win, val_line, pc_line, active_tab):
    if not stored:
        return warning_plot("⚠ No data available (stored problem)")

#     if active_tab not in ["tab3", "tab4", "tab5", "tab6"]:
#        raise dash.exceptions.PreventUpdate
    # Recreate the series from stored data
    series = pd.Series(data=stored["series"]["values"], index=stored["series"]["index"])

    # Convert selected flags into a dict of bools
    plot_flags = {flag: (flag in kde_flags) for flag in [
        "Latest", "bb1", "bb2", "local_mean", "local_xn", "local_bb",
        "mean", "med", "mod", "pc_line", "val_line", "band68", "band95"
    ]}

    # print("plot_flags =", plot_flags)

    # Build the figure
    return plot_main_kde(  
        plot_flags=plot_flags,
        Comdty=stored['comdty'],
        str_name=stored['str_name'],
        str_number=stored['str_number'],
        lookback_prd=stored.get('lookback_prd', 250),
        series=series,
        pc_line=pc_line if plot_flags.get("pc_line") else None,
        val_line=val_line if plot_flags.get("val_line") else None,
        local_win=local_win if any(plot_flags.get(f) for f in ["local_mean", "local_xn", "local_bb"]) else None,
        local_std=1
    )


######################################################################################
@app.callback(
    Output("cycle-store", "data"),
    [
        Input("stored-data", "data"),
        Input("base-str-input", "value"),
        Input("sum-first-n-base-input", "value"),
        Input("hike-threshold-input", "value"),
        Input("ease-threshold-input", "value"),
    ]
)
def classify_and_store(stored, base_str, sum_first_n_base, hike_threshold, ease_threshold):
    if not stored or "series" not in stored or "out_df" not in stored:
        return {}
    #print(base_str, sum_first_n_base, hike_threshold, ease_threshold)
    series = pd.Series(
        data= stored["series"]["values"],
        index= pd.to_datetime(stored["series"]["index"])
    )
    if series.empty:
        return {}
    comdty= stored["comdty"]
    out_df = pd.DataFrame(
        data=stored["out_df"]["data"],
        index=pd.to_datetime(stored["out_df"]["index"]),
        columns=stored["out_df"]["columns"]
    )
    if out_df.empty:
        return {}

    lookback_prd= stored["lookback_prd"]
    base_df= process_help_calculation(comdty, out_df, base_str, lookback_prd, 15)
    sum_first_n_base = int(sum_first_n_base)
    hike_threshold = float(hike_threshold)
    ease_threshold = float(ease_threshold)

    hike_cycle, ease_cycle, side_ways = classify_cycle(
        series= series,
        comdty= comdty,
        out_df= out_df,
        lookback_prd= lookback_prd,
        base_str=base_str,
        sum_first_n_base=sum_first_n_base,
        hike_threshold=hike_threshold,
        dovish_threshold=ease_threshold,
    )

    return {
        "hike": list(hike_cycle),
        "ease": list(ease_cycle),
        "sideways": list(side_ways)
     }


# ------------------------------------------------
# CALLBACK: hike-KDE Plot (Tab 4 - Copycat)
# ------------------------------------------------

@app.callback(
    Output('hike-kde-plot', 'figure'),
    [
        Input('stored-data', 'data'),
        Input("cycle-store", "data"),
        Input('kde-flags-shared', 'value'),
        Input('kde-local-win-shared', 'value'),
        Input('kde-val-line-shared', 'value'),
        Input('kde-pc-line-shared', 'value'),
        Input('tabs', 'value')
    ],
    prevent_initial_call=False
)
def update_kde_plot_tab4(stored, cycle_store, kde_flags, local_win, val_line, pc_line, active_tab):
    if active_tab != "tab4":
        raise dash.exceptions.PreventUpdate
    #print("hello hike")
    if not stored:
        return warning_plot("⚠ No 'Hike' cycle data available as per your criteria (no parent data)")
    
    if stored["comdty"] in {"VIX", "FVS", "meets", "SR1","SZI0", "VIX- VOXX" }:
        return warning_plot("⚠ Not relevent")
           
    # Parse full series
    series = pd.Series(
    data=stored["series"]["values"],
    index=pd.to_datetime(stored["series"]["index"])
    )

    # Build plot_flags
    plot_flags = {flag: (flag in kde_flags) for flag in [
        "Latest", "bb1", "bb2", "local_mean", "local_xn", "local_bb",
        "mean", "med", "mod", "pc_line", "val_line", "band68", "band95"
    ]}
    
    # Check for subseries (hike cycle)
    if cycle_store and 'hike' in cycle_store:
        sub_series = pd.Series(cycle_store["hike"])
        print("hike points", len(sub_series))
    else:
        return warning_plot("⚠ No 'Hike' cycle data available as per your criteria (before plotted)")
            
    return plotted(
        plot_flags=plot_flags,
        Comdty=stored['comdty'],
        str_name=stored['str_name'],
        str_number=stored['str_number'],
        sub_series=sub_series,
        full_series=series,
        pc_line=pc_line if plot_flags.get("pc_line") else None,
        val_line=val_line if plot_flags.get("val_line") else None,
        local_win=local_win if any(plot_flags.get(f) for f in ["local_mean", "local_xn", "local_bb"]) else None,
        local_win_std=1,
        cycle_name="Hike cycle"
    )



# ------------------------------------------------
# CALLBACK: ease-KDE Plot (Tab 5 - Copycat)
# ------------------------------------------------
@app.callback(
    Output('ease-kde-plot', 'figure'),
    Input('stored-data', 'data'),
    Input("cycle-store", "data"),
    Input('kde-flags-shared', 'value'),
    Input('kde-local-win-shared', 'value'),
    Input('kde-val-line-shared', 'value'),
    Input('kde-pc-line-shared', 'value'),
    Input('tabs', 'value'),  # 🆕 added
    prevent_initial_call=False
)
def update_kde_plot_tab5(stored, cycle_store, kde_flags, local_win, val_line, pc_line, active_tab):
    if active_tab != "tab5":
        raise dash.exceptions.PreventUpdate

    if not stored:
        return warning_plot("⚠ No 'Ease' cycle data available as per your criteria (no parent data)")

    if stored["comdty"] in {"VIX", "FVS", "meets", "SR1","SZI0", "VIX- VOXX" }:
        return warning_plot("⚠ Not relevent")
    # Parse full series
    series = pd.Series(data=stored["series"]["values"], index=stored["series"]["index"])

    # Build plot_flags
    plot_flags = {flag: (flag in kde_flags) for flag in [
        "Latest", "bb1", "bb2", "local_mean", "local_xn", "local_bb",
        "mean", "med", "mod", "pc_line", "val_line", "band68", "band95"
    ]}

    # Check for subseries (hike cycle)
    if cycle_store and 'ease' in cycle_store:
        sub_series = pd.Series(cycle_store["ease"])
        print("ease points", len(sub_series))
    else:
        return warning_plot("⚠ No 'Ease' cycle data available as per your criteria (before plotted)")

    return plotted(
        plot_flags=plot_flags,
        Comdty=stored['comdty'],
        str_name=stored['str_name'],
        str_number=stored['str_number'],
        sub_series=sub_series,
        full_series=series,
        pc_line=pc_line if plot_flags.get("pc_line") else None,
        val_line=val_line if plot_flags.get("val_line") else None,
        local_win=local_win if any(plot_flags.get(f) for f in ["local_mean", "local_xn", "local_bb"]) else None,
        local_win_std=1,
        cycle_name="Ease cycle"
    )

# # -----------------------------------------------------------------------------------------------------
# # CALLBACK: side-KDE Plot (Tab 6 - Copycat)
# # -------------------------------------------------------------------------------------------------------
@app.callback(
    Output('side-kde-plot', 'figure'),
    Input('stored-data', 'data'),
    Input("cycle-store", "data"),
    Input('kde-flags-shared', 'value'),
    Input('kde-local-win-shared', 'value'),
    Input('kde-val-line-shared', 'value'),
    Input('kde-pc-line-shared', 'value'),
    Input('tabs', 'value'),  # 🆕 added
    prevent_initial_call=False
)

def update_kde_plot_tab6(stored, cycle_store, kde_flags, local_win, val_line, pc_line, active_tab):
    if active_tab != "tab6":
        raise dash.exceptions.PreventUpdate
    if not stored:
        return warning_plot("⚠ No 'Side' ways cycle data available as per your criteria (no parent data)")

    if stored["comdty"] in {"VIX", "FVS", "meets", "SR1","SZI0", "VIX- VOXX" }:
        return warning_plot("⚠ Not relevent")
    # Parse full series
    series = pd.Series(data=stored["series"]["values"], index=stored["series"]["index"])

    # Build plot_flags
    plot_flags = {flag: (flag in kde_flags) for flag in [
        "Latest", "bb1", "bb2", "local_mean", "local_xn", "local_bb",
        "mean", "med", "mod", "pc_line", "val_line", "band68", "band95"
    ]}
    # Check for subseries (side ways cycle)
    #print("cs", len(cycle_store),len(cycle_store["sideways"]) )
    if cycle_store and 'sideways' in cycle_store:
        sub_series = pd.Series(cycle_store["sideways"])
        print("side ways points", len(sub_series))
    else:
        return warning_plot("⚠ No 'Side' ways cycle data available as per your criteria (before plotted)")
            
    return plotted(
        plot_flags=plot_flags,
        Comdty=stored['comdty'],
        str_name=stored['str_name'],
        str_number=stored['str_number'],
        sub_series=sub_series,
        full_series=series,
        pc_line=pc_line if plot_flags.get("pc_line") else None,
        val_line=val_line if plot_flags.get("val_line") else None,
        local_win=local_win if any(plot_flags.get(f) for f in ["local_mean", "local_xn", "local_bb"]) else None,
        local_win_std=1,
        cycle_name="Side ways cycle"
    )




def warning_plot(warning):
    fig = go.Figure()
    fig.add_annotation(
        #text="⚠ No 'Hike' cycle data available as per your criteria ",
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

# ------------------------------------------------
# MAIN
# ------------------------------------------------
if __name__ == '__main__':
    #app.run(debug= False, host='0.0.0.0', port=8050)# for live
    app.run(debug= True)
