# A Dash app to explore structure curve data: Curve view, chart and KDE analysis

import os
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, ctx, callback, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash.dependencies import ALL
# Custom modules
from str_cal import process_structure, extract_comdty,process_help_calculation, index , get_ratio, fetch_rates_cycle
from curve_plotter import plot_single_structure, get_button_class, compute_correlation_parameters
from curve_plotter import generate_curve_plot, cal_sum_of_eases_hikes,cal_sum_of_same_sign_meets, Out_tab2_2 ,S12_tab2_2,L6_tab2_2, add_chart_2_2, plot_chart_2_2,add_chart_2_3, plot_chart_2_3, build_button
from kde_help import plot_main_kde, classify_cycle, plotted
from matrix import build_button_tab7, get_button_class_tab7, generate_heatmap, compute_3d_structure, compute_percentile_df, compute_risk_reward_roll_df
from footer import footer_component, send_feedback_email

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



# dcc.Store(id='kde-shared-store', storage_type='session',
#     data={
#         'flags': ["Latest", "local_mean", "band68","band95" ],
#         'local_win': 10,
#         'val_line': 0,
#         'pc_line': 95
#     })
#wrapper for easy styling and clarity needed to add in layout 
dbc.Container(
    id="kde-flags-shared-wrapper",
    children=get_kde_controls(),
    className="kde-floating-panel-css",
    style={"display": "none"}  # Hidden by default
)

########################################### tab2_2 buttons #################################################
tab_2_2_2_3_button_ids = [
    "btn-ease_hike",
    "btn-nth_out",
    "btn-mid_out",
    "btn-1sts12",
    "btn-nths12",
    "btn-12ths12",
    "btn-nthl6",
    "btn-effr",
    "btn-2yr",
    "btn-5yr",
    "btn-10yr",

     "btn-ease_hike_3twin",
    "btn-nth_out_3twin",
    "btn-mid_out_3twin",
    "btn-1sts12_3twin",
    "btn-nths12_3twin",
    "btn-12ths12_3twin",
    "btn-nthl6_3twin",
    "btn-effr_3twin",
    "btn-2yr_3twin",
    "btn-5yr_3twin",
    "btn-10yr_3twin",
]
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
}

############################################# tab7  buttons ##############################
matrix_buttons=[
    "btn-price",
    "btn-percentile",
    "btn-rank5_95",
    "btn-rank1090",
    "btn-riskrewarddiff",
    "btn-riskreward",
    "btn-rolldown",
    "btn-momentum",
    "btn-rangebound",
    "btn-oi",
    "btn-volume",
]
default_tab7 = {
    "btn-price": True,
    "btn-percentile": True,
    "btn-rank5_95": False,
    "btn-rank1090": False,
    "btn-riskrewarddiff": False,
    "btn-riskreward": False,
    "btn-rolldown": False,
    "btn-momentum": False,
    "btn-rangebound": False,
    "btn-oi": False,
    "btn-volume": False,
}





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
                value="SR3_ED.xlsm" if "SR3_ED.xlsm" in excel_files else "SR3.xlsx" if "SR3.xlsx" in excel_files  else excel_files[0] if excel_files else None,
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
    # dcc.Store(id='kde-shared-store', storage_type='session',
    # data={
    #     'flags': ["Latest", "local_mean", "band68","band95" ],
    #     'local_win': 10,
    #     'val_line': 0,
    #     'pc_line': 95
    # }),
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
                    children=html.Div(dcc.Graph(id='curve-plot', config={'scrollZoom': True, 'displayModeBar': False}),className="border p-1 my-2 rounded")), width=10),
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
                    dbc.Col(dbc.Label("Local win"), width=6),
                    dbc.Col(dbc.Input(id="win-local", type="number", value=20, min=1, step=5, debounce=True), width=6)
                ], id="win-local-row", className="mb-2", style={"display": "none"}),

                dbc.Row([
                    dbc.Col(dbc.Label("Settle offset"), width=7),
                    dbc.Col(dbc.Input(id="Settle_days-input", type="number", value=10, min=1, step=5, debounce=True), width=5)
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
                    dbc.Col(dbc.Label("Quantile"), width=3),
                    dbc.Col(dbc.Input(id="quantile-input", type="number", value=95, min=0, max=100, step=5, debounce=True), width=9)
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

            ])
        ]),
###################################################  tab 2 ##############################################################################

dcc.Tab(
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
                            build_button("10 Yr", id="btn-10yr",active=default_2_2_2_3["btn-10yr"]),
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
),
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
    dcc.Tab(
    label='Matrix Filter',
    value='tab7',
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
        # Main row for the tab content
        dbc.Row([

            dcc.Store(id="fullscreen-mode", data=False),
            # Overlay expand button
            html.Button(
                "⤢",  # Unicode for "expand"
                id="expand-plot-btn",
                style={
                    "position": "absolute", "top": "-48px", "left": "78%", "zIndex": 10,
                    "background": "rgba(44, 62, 80, 0.5)", "border": "none", "color": "#fff","display": "flex", "alignItems": "center", "justifyContent": "center",
                    "borderRadius": "50%", "width": "40px","height": "50px", "padding": "0px", "cursor": "pointer", "fontSize": "25px"
                    ,"transform": "translateX(-100%)",  # Keeps the button within the parent edge
                },
                title="Expand Plot to Fullscreen",
                n_clicks=0,
            ),

            # ⬅️ Left Side — Heatmap
            dbc.Col([
                dcc.Loading(
                    id="loading-heatmap",
                    type="circle",
                    children=html.Div([
                        dcc.Graph(id="heatmap-matrix", config={'scrollZoom': True, 'displayModeBar': False}),
                    ], className="border p-2 my-2 rounded")
                )
            ], width=10, id= "plot-col-wid"),

            # 🎛️ Right Side — Controls Panel
            dbc.Col(
                className="control-panel-1",style={"marginTop": "5px"},
                children=[
                    html.H5(
                        "Plot Controls",
                        style={
                            "color": "#c0c4cc", "textAlign": "center", "padding": "8px 16px",
                            "backgroundColor": "#2b2e35", "fontWeight": "500", "fontSize": "16px",
                            "border": "1px solid #3a3f4b", "borderTopLeftRadius": "8px",
                            "borderTopRightRadius": "8px", "margin": "0"
                        }
                    ),
                    html.Div([
                        html.Div(
                            "Matrix view",
                            className="fw-bold small px-2 py-1",
                            style={
                                "backgroundColor": "#1f2128", "borderBottom": "1px solid #3a3f4b",
                                "borderTopLeftRadius": "6px", "borderTopRightRadius": "6px",
                                "color": "#c0c4cc", "fontWeight": "500", "textAlign": "center",
                                "padding": "8px 16px",
                            }
                        ),
                        html.Div([
                            html.Div([
                                html.Label("Local Window", className="form-label", style={"width": "68%", "marginBottom": 0}),
                                dcc.Input(
                                    id="input-local-window", type="number", min=1, value=21,
                                    debounce=False, placeholder="#", className="form-control form-control-sm",
                                    style={"width": "32%"}
                                )
                            ], className="d-flex justify-content-between mb-2"),

                            html.Div([
                                html.Label("Curve Length", className="form-label", style={"width": "68%", "marginBottom": 0}),
                                dcc.Input(
                                    id="input-curve-length", type="number", min=4, value=15,
                                    debounce=False, placeholder="#", className="form-control form-control-sm",
                                    style={"width": "32%"}
                                )
                            ], className="d-flex justify-content-between mb-2"),
                        ], style={"padding": "12px 10px 10px 10px"})

                    ], style={
                        "border": "1px solid #3a3f4b", "borderRadius": "6px",
                        "backgroundColor": "#2b2e35", "margin": "10px 0 18px 0"
                    }),

                    html.Div([
                        # Section title

                        dcc.Store(id='tab7-buttons-store', data=default_tab7),
                        html.Div(
                            "Metric",
                            className="fw-bold small px-2 py-1",
                            style={
                                "backgroundColor": "#1f2128",
                                "borderBottom": "1px solid #3a3f4b",
                                "borderTopLeftRadius": "6px",
                                "borderTopRightRadius": "6px",
                                "color": "#c0c4cc",
                                "fontWeight": "500",
                                "textAlign": "center",
                                "padding": "8px 16px"
                            }
                        ),
 
                        #expand button
                   
                        # Button group
                        dbc.ButtonGroup([
                            build_button_tab7("Price", id="btn-price",  active=default_tab7["btn-price"]),
                            build_button_tab7("Percentile", id="btn-percentile",  active=default_tab7["btn-percentile"]),
                            build_button_tab7("≤ 5 or ≥ 95", id="btn-rank5_95",  active=default_tab7["btn-rank5_95"]),
                            build_button_tab7("≤ 10 or ≥ 90", id="btn-rank1090",  active=default_tab7["btn-rank1090"]),
                            build_button_tab7("Risk/ Reward diff", id="btn-riskrewarddiff",  active=default_tab7["btn-riskrewarddiff"]),
                            build_button_tab7("Risk/Reward", id="btn-riskreward",  active=default_tab7["btn-riskreward"]),
                            build_button_tab7("Roll down", id="btn-rolldown",  active=default_tab7["btn-rolldown"]),
                            build_button_tab7("Momentum", id="btn-momentum",  active=default_tab7["btn-momentum"]),
                            build_button_tab7("Range bound", id="btn-rangebound",  active=default_tab7["btn-rangebound"]),
                            build_button_tab7("OI", id="btn-oi",  active=default_tab7["btn-oi"]),
                            build_button_tab7("Volume", id="btn-volume",  active=default_tab7["btn-volume"]),
                        ], vertical=True, className="mb-3 w-100", style={"padding": "10px 12px 6px 12px"})
                    ]), 

                    html.Div(id="matrix-filter-info", className="text-muted small mt-2")
                ],
                width=2, id= "control-col-wid"
            )
        ],style={"position": "relative"})
    ]
),




################################################################# tab 8 ###################################################
    dcc.Tab(label='Snapshot', value='tab8',
    style={"height": "42px","borderRadius": "8px 8px 0 0","padding": "8px 16px","marginRight": "4px","backgroundColor": "#2b2e35","color":  "#c0c4cc","fontWeight": "500","border": "1px solid #3a3f4b","borderBottom": "none","transition": "background-color 0.3s, color 0.3s"
        },
    selected_style={"height": "45px","borderRadius": "8px 8px 0 0","padding": "8px 16px","backgroundColor": "#1f2128","color": "#ffffff","fontWeight": "600","border": "1px solid #5e636e","borderBottom": "none","boxShadow": "0px -2px 6px rgba(0, 0, 0, 0.4)"
        },

    ),
]),  # ← close Tabs here

   
html.Hr(),
footer_component, 




    dcc.Store(id='stored-data', storage_type='local' ),#persistence=True
    dcc.Store(id='cycle-store',storage_type='local' )#persistence=True
    #html.Div(id='output-area', className='border p-3 my-2')


], fluid=True)  # ← close Container here


#

      # separator before footer







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

# --------------------------------------------------------------------------------------------------------------------------------------
# CALLBACK: Single Structure Plot (Tab 2)
# ---------------------------------------------------------------------------------------------------------------------------------------

@app.callback(
    Output('chart-plot', 'figure'),
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
    return plot_single_structure(series, str_name)

##################### tab 2_2 #############################################################################

@app.callback(
    Output("tab_2_2_2_3_toggle-store", "data"),
    [Input(btn_id, "n_clicks") for btn_id in tab_2_2_2_3_button_ids],
    State("tab_2_2_2_3_toggle-store", "data"),
    prevent_initial_call=True
)
def toggle_buttons(*args):
    store = args[-1] or {}
    triggered_id = ctx.triggered_id
    if triggered_id:
        current = store.get(triggered_id, False)
        store[triggered_id] = not current

         # Sync with copy/original:
        if triggered_id.endswith("_3twin"):
            twin_id = triggered_id[:-6]  # Remove '-3twin'
        else:
            twin_id = triggered_id + "_3twin"
        store[twin_id] = not current
    return store


@app.callback(
    [Output(btn_id, "className") for btn_id in tab_2_2_2_3_button_ids],
    Input("tab_2_2_2_3_toggle-store", "data")
)
def update_classnames(store):
    return [get_button_class(store.get(btn_id, False)) for btn_id in tab_2_2_2_3_button_ids]


@app.callback(
    Output('sum-of-eases-plot', 'figure'),
    Input('stored-data', 'data'),
    Input('tab_2_2_2_3_toggle-store', 'data'),
    Input('tabs', 'value'), # Optional
    prevent_initial_call=True
)
def update_tab_2_2(stored, toggle_store, tab):

    if not stored:
        return warning_plot("⚠ Series data not availbale (no stored data)")
    
    comdty= stored["comdty"]
    out_df = pd.DataFrame( 
        data=stored["out_df"]["data"],
        index=pd.to_datetime(stored["out_df"]["index"]),
        columns=stored["out_df"]["columns"]
    )
    lookback_prd= stored["lookback_prd"]
    

    fig2_2= plot_chart_2_2()
    active_buttons = 0
    for btn in tab_2_2_2_3_button_ids:
        if toggle_store.get(btn, False):
            active_buttons += 1
    if(active_buttons==0):
        return warning_plot("⚠ No series selected")

    chart2_1_series = stored['series']
    chart2_1_series = pd.Series(data=chart2_1_series['values'], index=pd.to_datetime(chart2_1_series['index']))
    
    if toggle_store.get("btn-ease_hike", False):
        if comdty == "meets":
            sum_of_ease_or_hikes= cal_sum_of_same_sign_meets(out_df,comdty, lookback_prd )
            #print(len(sum_of_ease_or_hikes))
        elif comdty in {"SR3", "ER", "SO3", "SA3", "CRA"}:
            sum_of_ease_or_hikes= cal_sum_of_eases_hikes(out_df, comdty, lookback_prd)
        else:
            sum_of_ease_or_hikes= pd.Series(dtype='float64')
        #print("len1", len(chart2_1_series), len(sum_of_ease_or_hikes))
        corr= compute_correlation_parameters(chart2_1_series, sum_of_ease_or_hikes)
        add_chart_2_2(fig2_2, sum_of_ease_or_hikes,corr, legend="sum of eases/ hikes" , color= "#4363d8") # Deep Blue

    if toggle_store.get("btn-nth_out", False):
        nth_out= Out_tab2_2(out_df, stored['str_number'], lookback_prd)
        corr= compute_correlation_parameters(chart2_1_series, nth_out)
        add_chart_2_2(fig2_2, nth_out,corr, legend="nth Out", color= "#f58231") # Orange
    
    if toggle_store.get("btn-mid_out", False):
        n= stored['str_number'] + int (len(get_ratio(stored['str_name'])) /2)
        mid_out= Out_tab2_2(out_df, n, lookback_prd)
        corr= compute_correlation_parameters(chart2_1_series, mid_out)
        add_chart_2_2(fig2_2, mid_out, corr,legend="Mid Out", color= "#ffe119") # Bright Yellow
    # for btn in tab2_2_button_ids:
    #     print(btn,toggle_store.get(btn))
    if toggle_store.get("btn-1sts12", False):
        firstS12= S12_tab2_2(out_df, 1 , lookback_prd)
        corr= compute_correlation_parameters(chart2_1_series, firstS12)
        add_chart_2_2(fig2_2, firstS12,corr, legend="1st S12", color= "#46f0f0")  # Cyan

    if toggle_store.get("btn-nths12", False):
        n= stored['str_number']
        nthS12= S12_tab2_2(out_df, n, lookback_prd)
        corr= compute_correlation_parameters(chart2_1_series, nthS12)
        add_chart_2_2(fig2_2, nthS12,corr, legend="nth S12", color= "#3cb44b")  # Strong Green

    if toggle_store.get("btn-12ths12", False):
        twelthS12= S12_tab2_2(out_df, 12, lookback_prd)
        corr= compute_correlation_parameters(chart2_1_series, twelthS12)
        add_chart_2_2(fig2_2, twelthS12,corr, legend="12th S12", color= "#f032e6") # Magenta

    if toggle_store.get("btn-nthl6", False):
        n= stored['str_number']
        nthl6= L6_tab2_2(out_df, n, lookback_prd)
        corr= compute_correlation_parameters(chart2_1_series, nthl6)
        add_chart_2_2(fig2_2, nthl6,corr, legend="nth L6", color= "rgb(152,78,163)")   

    if toggle_store.get("btn-effr", False):
        #["2Yr", "5Yr", "10Yr", "Rates"]
        df= fetch_rates_cycle(filepath= "SR3_ED.xlsm", sheetname= "treasuries rates", lookback_prd= lookback_prd )
        effr= df.loc["Rates"]  #effr(lookback_prd)
        #corr= compute_correlation_parameters(chart2_1_series, effr)
        corr= {
            'mean_rolling_correlation': None,
            'distance_correlation': None
        }
        add_chart_2_2(fig2_2, effr,corr, legend="EFFR", color= "black")  

    if toggle_store.get("btn-2yr", False):
        #["2Yr", "5Yr", "10Yr", "Rates"]
        df= fetch_rates_cycle(filepath= "SR3_ED.xlsm", sheetname= "treasuries rates", lookback_prd= lookback_prd)
        tr2= df.loc["2Yr"]  
        corr= compute_correlation_parameters(chart2_1_series, tr2)
        add_chart_2_2(fig2_2, tr2, corr, legend="2Yr", color= "#e6beff")   # Lavender

    if toggle_store.get("btn-5yr", False):
        #["2Yr", "5Yr", "10Yr", "Rates"]
        df= fetch_rates_cycle(filepath= "SR3_ED.xlsm", sheetname= "treasuries rates", lookback_prd= lookback_prd)
        tr5= df.loc["5Yr"]  
        corr= compute_correlation_parameters(chart2_1_series, tr5)
        add_chart_2_2(fig2_2, tr5, corr, legend="5Yr", color= "#bcf60c")  # Lime

    if toggle_store.get("btn-10yr", False):
        #["2Yr", "5Yr", "10Yr", "Rates"]
        df= fetch_rates_cycle(filepath= "SR3_ED.xlsm", sheetname= "treasuries rates", lookback_prd= lookback_prd)
        tr10= df.loc["10Yr"]  
        corr= compute_correlation_parameters(chart2_1_series, tr10)
        add_chart_2_2(fig2_2, tr10, corr, legend="10Yr", color= "#fabebe")  # Pink
    
    return fig2_2


########################################### tab_2_3 ################################################
@app.callback(
    Output('scatter_plot_2_3', 'figure'),
    Input('stored-data', 'data'),
    Input('tab_2_2_2_3_toggle-store', 'data'),
    Input('tabs', 'value'), # Optional
    prevent_initial_call=True
)
def update_tab_2_3(stored, toggle_store, tab):

    if not stored:
        return warning_plot("⚠ Series data not availbale (no stored data)")
    
    comdty= stored["comdty"]
    out_df = pd.DataFrame( 
        data=stored["out_df"]["data"],
        index=pd.to_datetime(stored["out_df"]["index"]),
        columns=stored["out_df"]["columns"]
    )
    lookback_prd= stored["lookback_prd"]
    

    fig2_3= plot_chart_2_3()
    active_buttons = 0
    for btn in tab_2_2_2_3_button_ids:
        if toggle_store.get(btn, False):
            active_buttons += 1
    if(active_buttons==0):
        return warning_plot("⚠ No series selected")

    chart2_1_series = stored['series']
    chart2_1_series = pd.Series(data=chart2_1_series['values'], index=pd.to_datetime(chart2_1_series['index']))
    
    if toggle_store.get("btn-ease_hike", False):
        if comdty == "meets":
            sum_of_ease_or_hikes= cal_sum_of_same_sign_meets(out_df,comdty, lookback_prd )
            #print(len(sum_of_ease_or_hikes))
        elif comdty in {"SR3", "ER", "SO3", "SA3", "CRA"}:
            sum_of_ease_or_hikes= cal_sum_of_eases_hikes(out_df, comdty, lookback_prd)
        else:
            sum_of_ease_or_hikes= pd.Series(dtype='float64')
        #print("len1", len(chart2_1_series), len(sum_of_ease_or_hikes))
        #corr= compute_correlation_parameters(chart2_1_series, sum_of_ease_or_hikes)
        add_chart_2_3(fig2_3,chart2_1_series, sum_of_ease_or_hikes, legend="sum of eases/ hikes" , color= "#4363d8") # Deep Blue

    if toggle_store.get("btn-nth_out", False):
        nth_out= Out_tab2_2(out_df, stored['str_number'], lookback_prd)
        #corr= compute_correlation_parameters(chart2_1_series, nth_out)
        add_chart_2_3(fig2_3, chart2_1_series, nth_out, legend="nth Out", color= "#f58231") # Orange
    
    if toggle_store.get("btn-mid_out", False):
        n= stored['str_number'] + int (len(get_ratio(stored['str_name'])) /2)
        mid_out= Out_tab2_2(out_df, n, lookback_prd)
        #corr= compute_correlation_parameters(chart2_1_series, mid_out)
        add_chart_2_3(fig2_3, chart2_1_series, mid_out, legend="Mid Out", color= "#ffe119") # Bright Yellow
    # for btn in tab2_2_button_ids:
    #     print(btn,toggle_store.get(btn))
    if toggle_store.get("btn-1sts12", False):
        firstS12= S12_tab2_2(out_df, 1 , lookback_prd)
        #corr= compute_correlation_parameters(chart2_1_series, firstS12)
        add_chart_2_3(fig2_3, chart2_1_series, firstS12, legend="1st S12", color= "#46f0f0")  # Cyan

    if toggle_store.get("btn-nths12", False):
        n= stored['str_number']
        nthS12= S12_tab2_2(out_df, n, lookback_prd)
        #corr= compute_correlation_parameters(chart2_1_series, nthS12)
        add_chart_2_3(fig2_3, chart2_1_series, nthS12, legend="nth S12", color= "#3cb44b")  # Strong Green

    if toggle_store.get("btn-12ths12", False):
        twelthS12= S12_tab2_2(out_df, 12, lookback_prd)
        #corr= compute_correlation_parameters(chart2_1_series, twelthS12)
        add_chart_2_3(fig2_3, chart2_1_series, twelthS12, legend="12th S12", color= "#f032e6") # Magenta

    if toggle_store.get("btn-nthl6", False):
        n= stored['str_number']
        nthl6= L6_tab2_2(out_df, n, lookback_prd)
        #corr= compute_correlation_parameters(chart2_1_series, nthl6)
        add_chart_2_3(fig2_3, chart2_1_series, nthl6, legend="nth L6", color= "rgb(152,78,163)")   

    if toggle_store.get("btn-effr", False):
        #["2Yr", "5Yr", "10Yr", "Rates"]
        df= fetch_rates_cycle(filepath= "SR3_ED.xlsm", sheetname= "treasuries rates", lookback_prd= lookback_prd )
        effr= df.loc["Rates"]  #effr(lookback_prd)
        #corr= compute_correlation_parameters(chart2_1_series, effr)
        # corr= {
        #     'mean_rolling_correlation': None,
        #     'distance_correlation': None
        # }
        add_chart_2_3(fig2_3, chart2_1_series, effr, legend="EFFR", color= "black")  

    if toggle_store.get("btn-2yr", False):
        #["2Yr", "5Yr", "10Yr", "Rates"]
        df= fetch_rates_cycle(filepath= "SR3_ED.xlsm", sheetname= "treasuries rates", lookback_prd= lookback_prd)
        tr2= df.loc["2Yr"]  
        #corr= compute_correlation_parameters(chart2_1_series, tr2)
        add_chart_2_3(fig2_3, chart2_1_series, tr2,  legend="2Yr", color= "#e6beff")   # Lavender

    if toggle_store.get("btn-5yr", False):
        #["2Yr", "5Yr", "10Yr", "Rates"]
        df= fetch_rates_cycle(filepath= "SR3_ED.xlsm", sheetname= "treasuries rates", lookback_prd= lookback_prd)
        tr5= df.loc["5Yr"]  
        #corr= compute_correlation_parameters(chart2_1_series, tr5)
        add_chart_2_3(fig2_3, chart2_1_series, tr5, legend="5Yr", color= "#bcf60c")  # Lime

    if toggle_store.get("btn-10yr", False):
        #["2Yr", "5Yr", "10Yr", "Rates"]
        df= fetch_rates_cycle(filepath= "SR3_ED.xlsm", sheetname= "treasuries rates", lookback_prd= lookback_prd)
        tr10= df.loc["10Yr"]  
        #corr= compute_correlation_parameters(chart2_1_series, tr10)
        add_chart_2_3(fig2_3, chart2_1_series, tr10, legend="10Yr", color= "#fabebe")  # Pink
    
    return fig2_3



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

############################################## tab 7 ############################################################################

@app.callback(
    Output("tab7-buttons-store", "data"),
    [Input(btn_id, "n_clicks") for btn_id in matrix_buttons],
    State("tab7-buttons-store", "data"),
    prevent_initial_call=True
)
def toggle_buttons(*args):
    store = args[-1] or {}
    triggered_id = ctx.triggered_id
    if triggered_id:
        current = store.get(triggered_id, False)
        store[triggered_id] = not current
    return store


@app.callback(
    [Output(btn_id, "className") for btn_id in matrix_buttons],
    Input("tab7-buttons-store", "data")
)
def update_classnames(store):
    return [get_button_class_tab7(store.get(btn_id, False)) for btn_id in matrix_buttons]

@callback(
    Output("fullscreen-mode", "data"),
    Output("plot-col-wid", "width"),
    Output("control-col-wid", "style"),
    Output("expand-plot-btn", "children"),
    Input("expand-plot-btn", "n_clicks"),
    State("fullscreen-mode", "data"),
    prevent_initial_call=True
)
def toggle_fullscreen(n_clicks, is_fullscreen):
    new_state = not is_fullscreen if n_clicks else is_fullscreen # Toggle the boolean fullscreen mode
    if new_state: 
        return new_state, 12, {"display": "none"}, "⤡"  # Fullscreen: plot is wide, controls hidden, icon is "restore"
    else: 
        return new_state, 10, {"display": "block"}, "⤢"# Default: plot normal width, controls visible, icon is "expand"

@app.callback(
    Output('heatmap-matrix', 'figure'),
    Input('stored-data', 'data'),
    Input('input-local-window', 'value'),
    Input('input-curve-length', 'value'),
    Input('tab7-buttons-store', 'data'),
    Input('tabs', 'value'), # Optional
    prevent_initial_call=True
    )
def update_tab_heatmap(stored,local_win, curve_len,  toggle_store, tab):
    if not stored:
        return warning_plot("⚠ data not availbale (no stored data)")
    
    comdty= stored["comdty"]
    out_df = pd.DataFrame( 
        data=stored["out_df"]["data"],
        index=pd.to_datetime(stored["out_df"]["index"]),
        columns=stored["out_df"]["columns"]
    )
    active_buttons=0 #priority list which values to be shown
    # do provide a ratio list which to plot according to each commodity
    # (out_df, structure_names, local_win=21, curve_length=15)
    str_data_3d= compute_3d_structure(out_df, local_win=local_win, curve_length=curve_len)
    latest_date = str_data_3d.index.get_level_values("Date").unique()[0]
    print("latest date in heatmap data", latest_date)
    for btn in matrix_buttons: #initial value populating
        if toggle_store.get("btn-price", False):
            latest_date = str_data_3d.index.get_level_values("Date").unique()[0]
            latest_df = str_data_3d.loc[(latest_date)] 
            heatmap= generate_heatmap(1, latest_df) 
            active_buttons+=1
            break
        elif toggle_store.get("btn-percentile", False) or toggle_store.get("btn-rank5_95", False) or toggle_store.get("btn-rank109", False):
            percentile_df = compute_percentile_df(str_data_3d) 
            heatmap= generate_heatmap(0, percentile_df) 
            active_buttons+=1
            break  
        elif toggle_store.get("btn-riskrewarddiff", False):
            latest_date = str_data_3d.index.get_level_values("Date").unique()[0]
            latest_df = str_data_3d.loc[(latest_date)] 
            risk_reward_df, risk_reward_diff_df, roll_down_df= compute_risk_reward_roll_df(latest_df)
            heatmap= generate_heatmap(1,risk_reward_diff_df) 
            active_buttons+=1
            break  
        elif toggle_store.get("btn-riskreward", False):
            latest_date = str_data_3d.index.get_level_values("Date").unique()[0]
            latest_df = str_data_3d.loc[(latest_date)] 
            risk_reward_df, risk_reward_diff_df, roll_down_df= compute_risk_reward_roll_df(latest_df)
            heatmap= generate_heatmap(1, risk_reward_df) 
            active_buttons+=1
            break
        elif toggle_store.get("btn-rolldown", False):
            latest_date = str_data_3d.index.get_level_values("Date").unique()[0]
            latest_df = str_data_3d.loc[(latest_date)] 
            risk_reward_df, risk_reward_diff_df, roll_down_df= compute_risk_reward_roll_df(latest_df)
            heatmap= generate_heatmap(1,roll_down_df) 
            active_buttons+=1
            break
        # elif toggle_store.get("btn-momentum" , False):
        #     mv_df= compute_mv_df(str_data_3d)
        #     heatmap= generate_heatmap(mv_df) 
        #     active_buttons+=1
        #     break  
        # elif toggle_store.get("btn-rangebound", False):
        #     rb_df= compute_rb_df(str_data_3d)
        #     heatmap= generate_heatmap(rb_df) 
        #     active_buttons+=1
        #     break   
    if(active_buttons==0):
        return warning_plot("⚠ No series selected")
    return heatmap

##################################################### footer callback ####################################################    
@callback(
    Output("trade-notes-store", "data"),
    Output("trade-note-input", "value"),
    Input("add-trade-note", "n_clicks"),
    Input({"type": "remove-note", "index": ALL}, "n_clicks"),
    State("trade-note-input", "value"),
    State("trade-notes-store", "data"),
    prevent_initial_call=True
)
def update_trade_notes(add_click, remove_clicks, new_note, stored_notes):
    stored_notes = stored_notes or []
    triggered = ctx.triggered_id

    if triggered == "add-trade-note":
        if new_note and new_note.strip():
            stored_notes.append(new_note.strip())
        return stored_notes, ""  # clear input after add

    if isinstance(triggered, dict) and triggered.get("type") == "remove-note":
        index = triggered.get("index")
        if index is not None and 0 <= index < len(stored_notes):
            stored_notes.pop(index)
        return stored_notes, no_update

    return no_update, no_update



@callback(
    Output("trade-note-list", "children"),
    Input("trade-notes-store", "data")
)
def display_trade_notes(notes):
    if not notes:
        return html.Div("No trades added yet.", style={"color": "#888", "padding": "10px"})

    return [
        html.Div([
            html.Span(note, style={"flexGrow": "1"}),

            html.Button("×", id={"type": "remove-note", "index": i}, n_clicks=0, 
                style={"backgroundColor": "transparent","border": "none","color": "#ffffff","fontSize": "16px","fontWeight": "bold","lineHeight": "1","cursor": "pointer","padding": "2px 6px","borderRadius": "4px","transition": "background 0.2s ease","marginLeft": "10px"
                })
        ], style={
            "fontSixe": "12px","display": "flex", "gap": "1px", "alignItems": "center", "marginBottom": "6px",
            "padding": "6px 10px", "backgroundColor": "#2a2d34","borderRadius": "6px"
        })
        for i, note in enumerate(notes)
    ]




################################################## Feedback Submit Callback########################################
@callback(
    Output("feedback-text", "value"),
    Output("submit-feedback", "children"),
    Output("reset-button-label", "disabled"),
    Input("submit-feedback", "n_clicks"),
    Input("reset-button-label", "n_intervals"),
    State("feedback-text", "value"),
    State("feedback-type", "value"),
    prevent_initial_call=True
)
def handle_feedback_and_reset(n_clicks, n_intervals, msg, category):
    # Identify what triggered the callback
    triggered = ctx.triggered_id

    if triggered == "submit-feedback" and msg and category:
        send_feedback_email(category, msg)
        return "", "Submitted ✅", False  # Enable timer

    elif triggered == "reset-button-label":
        return no_update, "Submit", True  # Reset label and disable interval

    return no_update, no_update, True


##########################################################################################################################################
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
    app.run(debug= False, host='0.0.0.0', port=8050)# for live
    #app.run(debug= True)
