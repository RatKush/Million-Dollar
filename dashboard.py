# A Dash app to explore structure curve data: Curve view, chart and KDE analysis
import os
import time
import socket
from typing import Optional, Union, Tuple, Dict, Any
import logging
import pandas as pd
import numpy as np
import dash
from dash import dcc, html, Input, Output, State, ctx, callback, no_update
from dash.dependencies import ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from flask_caching import Cache
import plotly.graph_objects as go
import dash_ag_grid as dag
# 1. THE ENTERPRISE SCRIPT for adding sprakline in table
external_scripts = ["https://cdn.jsdelivr.net/npm/ag-grid-enterprise/dist/ag-grid-enterprise.min.js"]
# Data processing and calculations
from str_cal import (
    extract_comdty,  process_raw_data, index, get_ratio, fetch_rates_cycle,fn_main_series_only, process_structure_data
)

# Curve plotting and visualization
from curve_plotter import (
    plot_single_structure, get_button_class, compute_correlation_parameters, generate_curve_plot, table_populating_1_2,
    cal_sum_of_eases_hikes, cal_sum_of_same_sign_meets, Out_tab2_2, S12_tab2_2, 
    L6_tab2_2, add_chart_2_2, plot_chart_2_2, add_chart_2_3, 
    plot_chart_2_3, build_button
)

# KDE analysis
from kde_help import plot_main_kde, classify_cycle, plotted_sub_KDE

# Matrix and heatmap functionality
from matrix import (
    build_button_tab7, get_button_class_tab7, generate_heatmap, color_heatmap,
    create_blank_heatmap, compute_3d_structure, compute_percentile_df,compute_zscore_df, compute_range_df,classify_regime_in_series,
    compute_risk_reward_roll_df, hovertemplate_heatmap, generate_heatmap_detail_panel,
    get_adjacent_values, filter_grey
)

# UI components
from footer import footer_component, send_feedback_email
# dashboard.py (top of file)
DEFAULT_CURVE_LENGTH = 20
DEFAULT_LOOKBACK = 250
DEFAULT_WINDOW = 21
DEFAULT_OUTLIER_K = 2.5

# ------------------------------------------------
# UTILITY: Read all available Excel files in local directory
# ------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
SUPPORTED_EXCEL_EXTENSIONS = ('.xlsx', '.xlsm', '.csv')
DEFAULT_FILES = ["SR3_ED.xlsm", "SR3.xlsx"]
def get_excel_files(directory_path: str = '.') -> list[str]:
    try:
        if not os.path.exists(directory_path):
            raise OSError(f"Directory does not exist: {directory_path}")

        if not os.path.isdir(directory_path):
            raise OSError(f"Path is not a directory: {directory_path}")

        excel_files = [
            filename for filename in os.listdir(directory_path) 
            if filename.lower().endswith(SUPPORTED_EXCEL_EXTENSIONS)
        ]

        return sorted(excel_files)  # Return sorted list for consistency

    except OSError as e:
        print(f"Error accessing directory {directory_path}: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error in get_excel_files: {e}")
        return []

def get_default_filename_comdty (available_files: list[str]) -> Optional[str]:
    if not available_files:
        return None,None

    # Check for preferred files in order of priority
    for preferred_file in DEFAULT_FILES:
        if preferred_file in available_files:
            com= extract_comdty(preferred_file)
            return preferred_file, com

    # If no preferred files found, return the first available file
    return available_files[0], extract_comdty(available_files[0])




# ------------------------------------------------remove_outliers
# DASH APP INITIALIZATION
# ------------------------------------------------
# Application configuration
APP_CONFIG = {
    'title': "Million Dollar",
    'theme': dbc.themes.CYBORG,
    'assets_folder': 'assets',
    'suppress_callback_exceptions': True,
    'cache_type': 'simple'  # Use 'filesystem' or 'redis' for production
}


def initialize_app() -> tuple[dash.Dash, Cache]:
    """
    Initialize the Dash application and cache system.

    This function creates and configures the main Dash application instance
    with proper theme, assets, and caching setup. It separates the initialization
    logic for better testability and configuration management.

    Returns:
        tuple[dash.Dash, Cache]: Configured Dash app and cache instances.
    """
    # Create Dash application instance
    app = dash.Dash(
        __name__, 
        assets_folder=APP_CONFIG['assets_folder'],
        external_stylesheets=[APP_CONFIG['theme']],
        external_scripts=external_scripts
    )

    # Configure application properties
    app.title = APP_CONFIG['title']
    app.config.suppress_callback_exceptions = APP_CONFIG['suppress_callback_exceptions']

    # Initialize cache system
    # Note: For production, consider using 'filesystem' or 'redis' cache types
    cache = Cache(app.server, config={
        'CACHE_TYPE': APP_CONFIG['cache_type']
    })

    return app, cache


# Get available Excel files and setup dropdown options
excel_files = get_excel_files()
filename_options = [{'label': filename, 'value': filename} for filename in excel_files]
default_filename, default_comdty = get_default_filename_comdty(excel_files)

# Initialize Dash application and cache
app, cache = initialize_app()



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
                        dcc.Input(id="hike-threshold-input", type="number", value=50, step=5, debounce=True,
                                className="form-control form-control-sm", style={"width": "32%"})
                    ], className="d-flex justify-content-between mb-2"),

                    html.Div([
                        html.Label("Ease Thrshld", className="form-label", style={"width": "68%", "marginBottom": 0}),
                        dcc.Input(id="ease-threshold-input", type="number", value=-50, step=5, debounce=True,
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
                {"label": "mean ± 1σ", "value": "bb1"},
                {"label": "mean ± 2σ", "value": "bb2"},
                {"label": "Median", "value": "med"},
                {"label": "% Line", "value": "pc_line"},
                {"label": "Val Line", "value": "val_line"},
                
            ],
            value=["Latest","med", "band68", "band95"],
            switch=True,
            className="px-3 mb-3"
        ),

        # html.Div([
        #     html.Label("Local Win", className="form-label", style={"width": "68%"}),
        #     dcc.Input(id="kde-local-win-shared", type="number", value=21, min=1, step=1, debounce=True, className="form-control form-control-sm", style={"width": "32%"})
        # ], className=" px-3 mb-2 hidden-row", id="kde-local-row"),

        html.Div([
            html.Label("Val Line", className="form-label", style={"width": "68%"}),
            dcc.Input(id="kde-val-line-shared", type="number", value=0, debounce=True, className="form-control form-control-sm", style={"width": "32%"})
        ], className=" px-3 mb-2 hidden-row", id="kde-val-row"),

        html.Div([
            html.Label("% Line", className="form-label", style={"width": "68%"}),
            dcc.Input(id="kde-pc-line-shared", type="number", value=95, min=0, max=100, step=1, debounce=True, className="form-control form-control-sm", style={"width": "32%"})
        ], className=" px-3 mb-2 hidden-row", id="kde-pc-row")

    ], className="control-panel-1")


#wrapper for easy styling and clarity needed to add in layout 
dbc.Container(
    id="kde-flags-shared-wrapper",
    children=get_kde_controls(),
    className="kde-floating-panel-css",
    style={"display": "none"}  # Hidden by default
)

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
############################################# tab7  buttons ##############################

default_tab7 = {
    "btn-price": True,
    "btn-percentile": False,
    "btn-zscore": False,
    "btn-riskrewarddiff": False,
    "btn-riskreward": False,
    "btn-rolldown": False,
    "btn-rollup": False,
    "btn-range": False,
    "btn-trend": False,
    "btn-oi": False,
    "btn-volume": False,

    #"btn-price_2": False,
    "btn-percentile_2": True,
    "btn-rank595_2": False,
    "btn-rank1090_2": False,
    "btn-zscore_2": False,
    "btn-riskrewarddiff_2": False,
    "btn-riskreward_2": False,
    "btn-rolldown_2": False,
    "btn-rollup_2": False,
    "btn-range_2": False,
    "btn-trend_2": False,
    "btn-oi_2": False,
    "btn-volume_2": False,
}

matrix_buttons_price= [k for k in default_tab7 if not k.endswith("_2")]
matrix_buttons_color= [k for k in default_tab7 if k.endswith("_2")]

##################################################### app layout #############################################################
# ------------------------------------------------
# DASH LAYOUT  my
# -----------------------------------------------
# UI layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Label("Filename", style={"color": "#c0c4cc", "fontWeight": "500",  "fontSize": "14px",   "marginBottom": "4px" }),
            dcc.Dropdown(
                id='filename',
                options=filename_options,
                value=default_filename,
                clearable=False,
                className='form-control'
            )
        ]),
        dbc.Col([
            html.Label("Comdty",style={"color": "#c0c4cc", "fontWeight": "500",  "fontSize": "14px",   "marginBottom": "4px" }),
            dcc.Loading(
                dcc.Input(id='comdty', type='text', value= default_comdty, disabled=True, className='form-control'),
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
            dcc.Input(id='curve_length', type='number', value=DEFAULT_CURVE_LENGTH, min= 5,  className='form-control')
        ]),
        dbc.Col([
            html.Label("Str Number", style={"color": "#c0c4cc", "fontWeight": "500",  "fontSize": "14px",   "marginBottom": "4px" }),
            dcc.Input(id='str_number', type='number', value=8, min=1, className='form-control')
        ]),
        dbc.Col([
            html.Label("Lookback Period", style={"color": "#c0c4cc", "fontWeight": "500",  "fontSize": "14px",   "marginBottom": "4px" }),
            dcc.Input(id='lookback_prd', type='number', value=DEFAULT_LOOKBACK, min=10, step=5, className='form-control')
        ]),
        dbc.Col([
            html.Label(" "),
            dbc.Button("Load", id='load-btn', color='primary', className='mt-4')
        ])
    ], className='mb-4'),


####################### kde -control for tab3, tab4, tab5, tab6--- needto declare beffore tabs declation#######################
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
                # dbc.Row([
                #     dbc.Col(dbc.Button("Load more", id="btn-more", color="secondary", size="sm", className="me-2"), width="auto"),
                #     dbc.Col(dbc.Button("Show all", id="btn-all", color="primary", size="sm", className="me-2"), width="auto"),
                #     dbc.Col(dbc.Button("Collapse", id="btn-collapse", color="dark", size="sm"), width="auto"),
                # ], className="my-2")
            
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
          #to trigger hover enrichment 
        dcc.Store(id='heatmap-ready-signal'),

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
                className="control-panel-1",style={"marginTop": "5px", "position": "relative"},
                children=[
                    # heatmap detail panel set to be invisible invisible
                    html.Div(
                        id='heatmap-details-panel',
                        className='details-panel', # class for CSS styling
                        style={'display': 'none'}, # Initially hidden
                        children=[],
                    ),

                    # control panel visible insitially 
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
                        #multi drop down 
                            html.Div([
                                html.Label("ratio", className="form-label", style={
                                    "marginBottom": "4px"  # optional: reduce space between label and box
                                }),
                                dcc.Dropdown(
                                    id='dropdown-ratio',
                                    options=[{'label': s, 'value': s} for s in index],
                                    value= index[0:27],
                                    multi=True,
                                    clearable=False,
                                    style={"width": "100%","maxHeight": "120px", "overflowY": "auto", "fontSize": "10px", "background-color": "#2b2e35", "color": "#ffffff"}  
                                )
                            ], id='dropdown-wrapper', className="mb-2", style={"width": "100%"})
,     

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
                                    id="input-curve-length", type="number", min=4, value=DEFAULT_CURVE_LENGTH,
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
                        dcc.Store(id='tab7-buttons-store-price', data=default_tab7),
                        dcc.Store(id='tab7-buttons-store-color', data=default_tab7),
                        dbc.Row([
                            # --- Left Column (50% width) ---
                            dbc.Col([
                                html.Div( # Thetitle for the left column.
                                    "Values",
                                    className="fw-bold small px-2 py-1",
                                    style={
                                        "backgroundColor": "#1f2128", "borderBottom": "1px solid #3a3f4b",
                                        "borderTopLeftRadius": "6px", "borderTopRightRadius": "6px",
                                        "color": "#c0c4cc", "fontWeight": "500", "textAlign": "center",
                                        "padding": "8px 16px"
                                    }
                                ),
                                # The original button group.
                                dbc.ButtonGroup([
                                    build_button_tab7("Price", id="btn-price", active=default_tab7["btn-price"]),
                                    build_button_tab7("Percentile", id="btn-percentile", active=default_tab7["btn-percentile"]),
                                    build_button_tab7("Z Score", id="btn-zscore", active=default_tab7["btn-zscore"]),
                                    build_button_tab7("Roll down", id="btn-rolldown", active=default_tab7["btn-rolldown"]),
                                    build_button_tab7("Roll up", id="btn-rollup", active=default_tab7["btn-rollup"]),
                                    build_button_tab7("RRd diff", id="btn-riskrewarddiff", active=default_tab7["btn-riskrewarddiff"]),
                                    build_button_tab7("Risk/ Reward", id="btn-riskreward", active=default_tab7["btn-riskreward"]),
                                    build_button_tab7("Range", id="btn-range", active=default_tab7["btn-range"]),
                                    build_button_tab7("Trend", id="btn-trend", active=default_tab7["btn-trend"]),
                                    build_button_tab7("OI", id="btn-oi", active=default_tab7["btn-oi"]),
                                    build_button_tab7("Volume", id="btn-volume", active=default_tab7["btn-volume"]),
                                ], vertical=True, className="mb-3 w-100", style={"padding": "10px 4px 6px 12px"})
                            ], width=6),  # width=6 makes this column take up half the space.

                            # --- Right Column (50% width) ---
                            dbc.Col([
                                # The "Metric" title for the right column.
                                html.Div(
                                    "Colors",  # You can use a different title for clarity.
                                    className="fw-bold small px-2 py-1",
                                    style={
                                        "backgroundColor": "#1f2128", "borderBottom": "1px solid #3a3f4b",
                                        "borderTopLeftRadius": "6px", "borderTopRightRadius": "6px",
                                        "color": "#c0c4cc", "fontWeight": "500", "textAlign": "center",
                                        "padding": "8px 16px"
                                    }
                                ),
                                # The duplicated button group with new, unique IDs.
                                dbc.ButtonGroup([
                                    #build_button_tab7("Price", id="btn-price_2", active=default_tab7["btn-price_2"]),
                                    build_button_tab7("Percentile", id="btn-percentile_2", active=default_tab7["btn-percentile_2"]),
                                    build_button_tab7("≤ 5 or ≥ 95", id="btn-rank595_2", active=default_tab7["btn-rank595_2"]),
                                    build_button_tab7("≤ 10 or ≥ 90", id="btn-rank1090_2", active=default_tab7["btn-rank1090_2"]),
                                    build_button_tab7("Z Score", id="btn-zscore_2", active=default_tab7["btn-zscore_2"]),
                                    build_button_tab7("RRd diff", id="btn-riskrewarddiff_2", active=default_tab7["btn-riskrewarddiff_2"]),
                                    build_button_tab7("Risk/ Reward", id="btn-riskreward_2", active=default_tab7["btn-riskreward_2"]),
                                    build_button_tab7("Roll down", id="btn-rolldown_2", active=default_tab7["btn-rolldown_2"]),
                                    build_button_tab7("Roll up", id="btn-rollup_2", active=default_tab7["btn-rollup_2"]),
                                    build_button_tab7("Range", id="btn-range_2", active=default_tab7["btn-range_2"]),
                                    build_button_tab7("Trend", id="btn-trend_2", active=default_tab7["btn-trend_2"]),
                                    build_button_tab7("OI", id="btn-oi_2", active=default_tab7["btn-oi_2"]),
                                    build_button_tab7("Volume", id="btn-volume_2", active=default_tab7["btn-volume_2"]),
                                ], vertical=True, className="mb-3 w-100", style={"padding": "10px 12px 6px 4px"})
                            ], width=6),  # width=6 makes this column take up the other half.
                        ])
                    ]), 

                    html.Div(id="matrix-filter-info", className="text-muted small mt-2")
                ],
                width=2, id= "control-col-wid"
            )
        ],style={"position": "relative"})
    ]
),
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



    dcc.Store(id='raw-data-store', storage_type='session'),
    dcc.Store(id='general-store', data=[default_comdty, "L6", 8, DEFAULT_LOOKBACK], storage_type='session'),
    dcc.Store(id='structure-data-store', storage_type='session'),
    dcc.Store(id='final-mainseriesonly-store', storage_type='session'),
    dcc.Store(id="shared-xrange_2_1_2_2"),   # hidden storage for sync
    dcc.Store(id='cycle-store',storage_type='session' ),#persistence=Tru


], fluid=True)  # ← close Container here


###############################################################################################################

      # separator before footer







################################################################ #########################################################
# ---------------------------------------------------------------------------------------------------
# CALLBACK: Load & Process raw data (outright) and Structure Data df and interested Series
# ------------------------------------------------------------------------------------------------------
def serialize_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Convert a pandas DataFrame to JSON-serializable dictionary - CORRECTED"""
    if df is None or df.empty:
        return {"data": [], "index": [], "columns": []}
    
    # Ensure index is serializable
    try:
        index_serialized = df.index.astype(str).tolist()
    except:
        index_serialized = list(range(len(df)))
    
    return {
        "data": df.values.tolist(),
        "index": index_serialized,
        "columns": df.columns.tolist()
    }


def serialize_series(series: pd.Series) -> Dict[str, Any]:
    """Convert a pandas Series to JSON-serializable dictionary - CORRECTED"""
    if series is None or series.empty:
        return {"values": [], "index": []}
    
    # Ensure index is serializable
    try:
        index_serialized = series.index.astype(str).tolist()
    except:
        index_serialized = list(range(len(series)))
    
    return {
        "values": series.values.tolist(),
        "index": index_serialized
    }

@callback(
    Output('general-store', 'data'),
    [Input('filename', 'value'),
    Input('str_name', 'value'),
    Input('str_number', 'value'),
    Input('lookback_prd', 'value')])
def general_info(filename, str_name, str_num, lookback_prd):
    if not filename or not str_name or not  str_num or not  lookback_prd :
        raise PreventUpdate # don’t update store if no file chosen

    comdty = extract_comdty(filename)
    str_name = str(str_name).strip().upper() if str_name else None
    str_num = int(str_num) if str_num and str(str_num).isdigit() else None
    lookback_prd = int(lookback_prd) if lookback_prd and str(lookback_prd).isdigit() else None

    # Return as list (JSON serializable)
    return [comdty, str_name, str_num, lookback_prd]


#populatinty comodity 
@callback(
    Output('comdty', 'value'),
    Input('general-store', 'data')
)
def update_comdty_input(general_data: list) -> str:
    """Updates the commodity input field based on the stored commodity data."""
    if not general_data or len(general_data) < 1:
        return ""
    return str(general_data[0])   # first element = comdty

@callback(
    Output('raw-data-store', 'data'),
    [Input('filename', 'value'),
     Input('lookback_prd', 'value')],
)
def extract_raw_data(filename: str, lookback_prd: Union[str, int]) -> Dict[str, Any]:
    """CORRECTED: Extract raw data callback - simplified validation"""
    # Basic validation - return empty if invalid inputs
    if not filename or not lookback_prd:
        raise PreventUpdate
    
    try:
        lookback_prd_int = int(lookback_prd)
        if lookback_prd_int <= 0:
            return {}
        
        # Load and process data - FIXED: now returns tuple
        raw_df = process_raw_data(filepath=filename, lookback_prd=lookback_prd_int)
        if raw_df.empty:
            return {}
        
        # Serialize the raw data for storage
        serialized_raw_data = serialize_dataframe(raw_df)
        return serialized_raw_data
        
    except Exception as e:
        logging.error(f"Error in extract_raw_data_callback for file {filename}: {e}")
        return {}




############################ ONLY MAIN SERIES cal ######################################################################
@callback(
    Output('final-mainseriesonly-store', 'data'),
    [Input('raw-data-store', 'data'),
    State('general-store', 'data'),
    Input('str_name', 'value'),
    Input('str_number', 'value'),
    Input('lookback_prd', 'value')],
)
def compute_main_series_only(raw_data_dict: Dict[str, Any], general_store, str_name, str_number, lookback_prd):
    if not raw_data_dict or not str_name or not general_store or not str_number or not lookback_prd:
        raise PreventUpdate
    
    try:
        if not raw_data_dict.get('data'):
            return {}
        
        raw_df = pd.DataFrame(
            data=raw_data_dict['data'],
            index=pd.to_datetime(raw_data_dict.get('index', None), errors='coerce', format='mixed'), # Convert back to DatetimeIndex
            columns=raw_data_dict.get('columns', None)
        )
        if raw_df.empty:
            return {}
        str_number_int = int(str_number)
        lookback_int = int(lookback_prd)
        return serialize_series( fn_main_series_only(raw_df,str_name,str_number_int, general_store[0],lookback_int))
        
    except Exception as e:
        print(f"Error in compute_main_series_only_callback: {e}")
        return {}






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


# -----------------------------------------------------------------------------------------------------
# CALLBACK: Curve Plot for Tab 1
# -----------------------------------------------------------------------------------------------------

########### str_df store #################
@app.callback(
    Output('structure-data-store', 'data'),
    Input('raw-data-store', 'data'),
    Input('win-local', 'value'),
    Input('str_name', 'value'),
    State('general-store', 'data'),
)
def store_str_df_dcc_(raw_data_dict, win_local,str_name,  general_store):
    if  not raw_data_dict or not raw_data_dict.get('data') :
        raise PreventUpdate

    inputs = [win_local]
    if any(x is None for x in inputs):
        raise PreventUpdate

    try:
        raw_df = pd.DataFrame(
            data=raw_data_dict['data'],
            index=pd.to_datetime(raw_data_dict.get('index', None), errors='coerce', format='mixed'), # Convert back to DatetimeIndex
            columns=raw_data_dict.get('columns', None)
        )
        if raw_df.empty:
            raise PreventUpdate

        local_win_for_str_df= min(win_local+ 21, raw_df.shape[0])
        sub_df = raw_df.iloc[:local_win_for_str_df, :]
        if not raw_df.empty:
            first_row_key = tuple(raw_df.iloc[0].values)
        else:
            first_row_key = "empty"

        # Cache key = index hash + first row + other params
        cache_key = f"str_df:{hash(tuple(raw_df.index))}:{first_row_key}:{general_store[0]}:{win_local}:{str_name}"
        str_df = cache.get(cache_key)
        
        if str_df is None:
            str_df = process_structure_data(sub_df,general_store[0],win_local,str_name)
            cache.set(cache_key, str_df)

        if str_df.empty:
            raise PreventUpdate
        return serialize_dataframe(str_df)
    except Exception as e:
        print(f"Error in computing str_df from raw_df: {e}")
        return {}
    




@app.callback(
    Output('curve-plot', 'figure'),
    Input('raw-data-store', 'data'),
    Input('curve_length', 'value'),
    Input('str_name', 'value'),
    State('general-store', 'data'),
    Input('plot-flags', 'value'),
    Input('Settle_days-input', 'value'),
    Input('date1-input', 'value'),
    Input('date2-input', 'value'),
    Input('win-local', 'value'),
    Input('quantile-input', 'value'),
    Input('bb-std-input', 'value'),
)
def update_curve_plot(raw_data_dict,  curve_len, str_name, general_store, active_flags, Settle_days, date1, date2, win_local, quantile, bb_std):
    if  not raw_data_dict or not raw_data_dict.get('data') :
        return warning_plot("⚠ No structure data available")

    inputs = [curve_len, Settle_days, date1, date2, win_local, quantile, bb_std]
    if any(x is None for x in inputs):
        raise PreventUpdate

    try:
        raw_df = pd.DataFrame(
            data=raw_data_dict['data'],
            index=pd.to_datetime(raw_data_dict.get('index', None), errors='coerce', format='mixed'), # Convert back to DatetimeIndex
            columns=raw_data_dict.get('columns', None)
        )
        if raw_df.empty:
            warning_plot("⚠ raw data empty after reconstruction")
        #print(raw_df.head())
        #raw_data,  comdty, local_win, str_name)
        local_win_for_str_df= min(win_local+ 21, raw_df.shape[0])
        #str_df= process_structure_data(raw_df.iloc[:local_win_for_str_df,:], general_store[0] , win_local,  general_store[1])
        # ---- Simple global cache ----
        sub_df = raw_df.iloc[:local_win_for_str_df, :]
                # Pick first row values as tuple (safe even if only one column)
        if not raw_df.empty:
            first_row_key = tuple(raw_df.iloc[0].values)
        else:
            first_row_key = "empty"

        # Cache key = index hash + first row + other params
        cache_key = f"str_df:{hash(tuple(raw_df.index))}:{first_row_key}:{general_store[0]}:{win_local}:{str_name}"
        str_df = cache.get(cache_key)
        
        if str_df is None:
            str_df = process_structure_data(sub_df,general_store[0],win_local,str_name)
            cache.set(cache_key, str_df)

        if str_df.empty:
            return warning_plot("⚠ Structure data empty after reconstruction")

        try:
            n = int(curve_len)
            if n <= 0:
                n = DEFAULT_CURVE_LENGTH
        except:
            n = DEFAULT_CURVE_LENGTH
        str_df = str_df.iloc[:, :min(n, str_df.shape[1])]

        
        # ✅ Normalize flags
        required_flags = ["Latest", "Settle", "Date1", "Date2", "MA", "MED", "quant_ser", "BB", "XN"]
        plot_flags = {key: key in (active_flags or []) for key in required_flags}

        # ✅ Convert dates safely
        date1 = pd.to_datetime(date1, errors="coerce", format='mixed') if plot_flags["Date1"] else None
        date2 = pd.to_datetime(date2, errors="coerce", format='mixed') if plot_flags["Date2"] else None

        #print(str_df.head())
        return generate_curve_plot(
            str_df=str_df,
            raw_df= raw_df,
            plot_flags=plot_flags,
            comdty= general_store[0],
            curve_len= curve_len,
            str_name= str_name,
            Settle=Settle_days if plot_flags["Settle"] else None,
            date1=date1,
            date2=date2,
            win_local=int(win_local) if win_local else 21,
            quantile=float(quantile) if plot_flags["quant_ser"] else None,
            bb_std=float(bb_std) if plot_flags["BB"] else None,
        )

    except Exception as e:
        logging.exception("update_curve_plot failed")
        return warning_plot(f"⚠ Failed to generate plot: {e}")


# # --------------------------------------------------------------------------------------------------------------------------------------
# # CALLBACK: table (Tab 1.2)
# # ---------------------------------------------------------------------------------------------------------------------------------------
@app.callback(
    Output('contracts-table', 'rowData'),
    Output('contracts-table', 'columnDefs'),
    Input('structure-data-store', 'data'),
    Input('curve_length', 'value'),
    Input('str_name', 'value'),
    Input('str_number', 'value'),
    Input('win-local', 'value'),
    State('general-store', 'data'),
)
def table_1_2_callback(str_data, curve_len,str_name, str_number,  win_local, general):
    # 2. DESERIALIZE DATA: Convert the stored dictionary back into a DataFrame
    try:
         # --- 1. Handle initial state ---
        if not str_data or "data" not in str_data:
            return [], []

        # --- 2. Deserialize into DataFrame safely ---
        try:
            df = pd.DataFrame(
                data=str_data.get("data", []),
                index=pd.to_datetime(str_data.get("index", []), errors="coerce"),
                columns=str_data.get("columns", []),
            )
        except Exception as e:
            logging.warning(f"Failed to deserialize str_data into DataFrame: {e}")
            return [], []
        if df.empty:
            return [], []
       
        # --- 3. Parameters ---
        try:
            change_period = int(win_local) if win_local and int(win_local) > 0 else 1
        except Exception:
            change_period = 1

        try:
            curve_len_final = int(curve_len) if curve_len and int(curve_len) > 0 else DEFAULT_CURVE_LENGTH
        except Exception:
            curve_len_final = DEFAULT_CURVE_LENGTH

        return table_populating_1_2(df, change_period, curve_len_final, str_name)


    except Exception as e:
        logging.exception("table populating failed")
        return [], []




# # --------------------------------------------------------------------------------------------------------------------------------------
# # CALLBACK: Single Structure Plot (Tab 2)
# # ---------------------------------------------------------------------------------------------------------------------------------------

@app.callback(
    Output('chart-plot', 'figure', allow_duplicate=True),
    Input('final-mainseriesonly-store', 'data'),
    State('general-store', 'data'),
    prevent_initial_call=True
)
def update_chart_tab(stored: Dict[str, Any], general) -> Any:
    """Rebuild Series and return plot."""
    if not stored or "values" not in stored or "index" not in stored:
        return warning_plot("⚠️ Series data not available")

    try:
        series = pd.Series(
        data=stored["values"],
        index=pd.to_datetime(stored["index"], errors="coerce")
        )
        str_name = f"{general[0]}{general[1]}({general[2]})"
        return plot_single_structure(series, str_name)

    except Exception as e:
        print(f"[update_chart_tab] Error: {e}")
        return warning_plot("⚠️ Failed to plot series")

# ##################### tab 2_2 #############################################################################
# ########################################### tab_2_3 ################################################

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
    [Output('sum-of-eases-plot', 'figure', allow_duplicate=True),
    Output('scatter_plot_2_3', 'figure')],
    [Input('raw-data-store', 'data'),
    State('general-store', 'data'),
    Input('final-mainseriesonly-store', 'data'),## tab2_1 series for corr
    Input('tab_2_2_2_3_toggle-store', 'data')],
    prevent_initial_call=True
)
def update_tab_2_2(raw_data_dict: Dict[str, Any], general_store, main_series: Dict[str, Any], toggle_store: dict):
    # Basic validation
    if not raw_data_dict or not raw_data_dict.get('data'):
        return warning_plot("no raw data dict found update_tab_2_2 "), warning_plot("no raw data dict found update_tab_2_3 ")
    
    raw_df = pd.DataFrame(
        data=raw_data_dict['data'],
        index=pd.to_datetime(raw_data_dict.get('index', None), errors='coerce', format='mixed'), # Convert back to DatetimeIndex
        columns=raw_data_dict.get('columns', None)
    )
    
    if raw_df.empty:
        return  warning_plot("no raw data found update_tab_2_2 "), warning_plot("no raw data found update_tab_2_3 ")
        
    comdty,str_name, str_num,lookback_prd= general_store[0], general_store[1],general_store[2],general_store[3]
    fig2_2 = plot_chart_2_2()
    fig2_3 = plot_chart_2_3()
    # Early exit if no buttons are toggled
    if not any(toggle_store.get(btn) for btn in tab_2_2_2_3_button_ids):
        return warning_plot("⚠ No series selected"), warning_plot("⚠ No series selected")

    """Rebuild main Series for corr"""
    if not main_series or "values" not in main_series or "index" not in main_series:
        chart2_1_series= None

    else:
        chart2_1_series = pd.Series(
            data=main_series["values"],
            index=pd.to_datetime(main_series["index"], errors="coerce")
        )

    # --- Trace Generation Configuration ---
    # Define a configuration map for most traces to reduce repetitive if-blocks
    
    trace_config = {
        "btn-nth_out": {
            "func": Out_tab2_2,
            "args": (raw_df,comdty, str_num, lookback_prd),
            "legend": "nth Out",
            "color": "#f58231" # Orange
        },
        "btn-mid_out": {
            "func": Out_tab2_2,
            "args": (raw_df, comdty, str_num + int(len(get_ratio(str_name)) / 2), lookback_prd),
            "legend": "Mid Out",
            "color": "#ffe119" # Bright Yellow
        },
        "btn-1sts12": {
            "func": S12_tab2_2,
            "args": (raw_df, 1, lookback_prd),
            "legend": "1st S12",
            "color": "#006666" # Cyan
        },
        "btn-nths12": {
            "func": S12_tab2_2,
            "args": (raw_df, str_num, lookback_prd),
            "legend": "nth S12",
            "color": "#3cb44b" # Strong Green
        },
        "btn-12ths12": {
            "func": S12_tab2_2,
            "args": (raw_df, 12, lookback_prd),
            "legend": "12th S12",
            "color": "#f032e6" # Magenta
        },
        "btn-nthl6": {
            "func": L6_tab2_2,
            "args": (raw_df, str_num, lookback_prd),
            "legend": "nth L6",
            "color": "rgb(152,78,163)"
        }
    }

    # --- Handle Special Cases & One-Offs ---

    # 1. Sum of eases/hikes
    if toggle_store.get("btn-ease_hike"):
        if comdty == "meets":
            series_data = cal_sum_of_same_sign_meets(raw_df, comdty, lookback_prd)
        elif comdty in {"SR3", "ER", "SO3", "SA3", "CRA", "ESTR"}:
            series_data = cal_sum_of_eases_hikes(raw_df, comdty, lookback_prd)
        else:
            series_data = pd.Series(dtype='float64')
        
        add_chart_2_3(fig2_3, chart2_1_series, series_data, legend="sum of eases/ hikes", color="#4363d8")
        corr = compute_correlation_parameters(chart2_1_series, series_data)
        add_chart_2_2(fig2_2, series_data, corr, legend="sum of eases/ hikes", color="#4363d8")

    # 2. Treasury rates (fetch data only once)
    treasury_buttons = {"btn-effr", "btn-2yr", "btn-5yr", "btn-10yr", "btn-2y10y"}
    if any(toggle_store.get(btn) for btn in treasury_buttons):
        df_rates = fetch_rates_cycle(filepath="SR3_ED.xlsm", sheetname="treasuries rates", lookback_prd=lookback_prd)
        
        treasury_map = {
            "btn-effr": {"label": "Rates", "legend": "EFFR", "color": "black"},
            "btn-2yr": {"label": "2Yr", "legend": "2Yr", "color": "#5c2791"},
            "btn-5yr": {"label": "5Yr", "legend": "5Yr", "color": "#7a9900"},
            "btn-10yr": {"label": "10Yr", "legend": "10Yr", "color": "#b04141"},
            "btn-2y10y": {"label": "2y10y", "legend": "2y10y", "color": "#8c564b"},
        }

        for btn, params in treasury_map.items():
            if toggle_store.get(btn):
                series_data = df_rates.loc[params["label"]]
                add_chart_2_3(fig2_3, chart2_1_series, series_data, legend=params["legend"], color=params["color"])
                if btn == "btn-effr":
                    # Special correlation case for EFFR
                    corr = {'mean_rolling_correlation': None, 'distance_correlation': None}
                else:
                    corr = compute_correlation_parameters(chart2_1_series, series_data)
                add_chart_2_2(fig2_2, series_data, corr, legend=params["legend"], color=params["color"])

    # --- Process Standard Traces from Config ---
    for btn, config in trace_config.items():
        if toggle_store.get(btn):
            series_data = config["func"](*config["args"])
            add_chart_2_3(fig2_3, chart2_1_series, series_data, legend=config["legend"], color=config["color"])
            corr = compute_correlation_parameters(chart2_1_series, series_data)
            add_chart_2_2(fig2_2, series_data, corr, legend=config["legend"], color=config["color"])

    return fig2_2, fig2_3



# #######################################3 syncing x-axis of fig 2_2 and fig 2_3 ###############
# # --- 1. Helper Function for Synchronization ---
# def sync_x_axis(relayout_data, current_figure):
#     if not relayout_data or 'xaxis.range[0]' not in relayout_data: # Guard clause: Do nothing if there's no relayoutData or it's not a zoom/pan event
#         return no_update

#     new_x_range = [relayout_data['xaxis.range[0]'], relayout_data['xaxis.range[1]']]
#     if 'xaxis' in current_figure['layout'] and 'range' in current_figure['layout']['xaxis']: # Check if the target figure's x-axis range is already the same to prevent circular updates
#         current_x_range = current_figure['layout']['xaxis']['range']
#         if current_x_range == new_x_range:
#             return no_update

#     # Create a new figure object to avoid modifying the original state directly
#     fig = go.Figure(data=current_figure['data'], layout=current_figure['layout'])
#     fig.update_layout(xaxis_range=new_x_range)   # Update the x-axis range
#     return fig

# #syncing
#     # --- 4. Refactored Callbacks ---
# @app.callback(
#     Output('chart-plot', 'figure', allow_duplicate=True),
#     Input('sum-of-eases-plot', 'relayoutData'),
#     State('chart-plot', 'figure'),
#     prevent_initial_call=True
# )
# def sync_chart_plot_from_sum_eases(relayout_data, current_figure):
#     return sync_x_axis(relayout_data, current_figure)


# @app.callback(
#     Output('sum-of-eases-plot', 'figure', allow_duplicate=True),
#     Input('chart-plot', 'relayoutData'),
#     State('sum-of-eases-plot', 'figure'),
#     prevent_initial_call=True
# )
# def sync_sum_eases_from_chart_plot(relayout_data, current_figure):
#     return sync_x_axis(relayout_data, current_figure)


# # ---------------------------------------------------------------------------------------------------------
# # CALLBACK:  shared KDE Input Toggle tab3 | tab4 | tab5 | tab6
# # ------------------------------------------------------------------------------------------------------------

# #rendering control panel in tab 3 to tab6
@app.callback(
    Output("kde-flags-shared-wrapper", "style"),
    Input("tabs", "value")
)
def toggle_kde_controls_visibility(active_tab):
    # Show only for Tab 3 to 6
    if active_tab in ['tab3', 'tab4', 'tab5', 'tab6']:
        return {"display": "block"}  # or use "flex" if you prefer
    return {"display": "none"}

# #invisibility 
@app.callback(
    [
        Output("kde-val-row", "style"),
        Output("kde-pc-row", "style")
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
    ]



# # # --------------------------------------------------------------------------------------------
# # # CALLBACK: KDE Plot (Tab 3)
# # # ----------------------------------------------------------------------------------------------------
@app.callback(
    Output('kde-plot', 'figure'),
    Input('final-mainseriesonly-store', 'data'),
    State('general-store', 'data'),
    Input('kde-flags-shared', 'value'),
    Input('kde-val-line-shared', 'value'),
    Input('kde-pc-line-shared', 'value'),
    prevent_initial_call=False
)
def update_kde_plot_tab3(stored,general_store, kde_flags, val_line, pc_line):
    if not stored or "values" not in stored or "index" not in stored:
        return warning_plot("⚠️ Series data not available")

   
    series = pd.Series(
    data=stored["values"],
    index=pd.to_datetime(stored["index"], errors="coerce")
    )
        
    # Convert selected flags into a dict of bools
    plot_flags = {flag: (flag in kde_flags) for flag in [
        "Latest", "bb1", "bb2", 
         "med",  "pc_line", "val_line", "band68", "band95"
    ]}

    # print("plot_flags =", plot_flags)
    comdty,str_name, str_num,lookback_prd= general_store[0], general_store[1],general_store[2],general_store[3]
    # Build the figure
    return plot_main_kde(  
        plot_flags=plot_flags,
        Comdty=comdty,
        str_name=str_name,
        str_number=str_num,
        lookback_prd=lookback_prd,
        series=series,
        pc_line=pc_line if plot_flags.get("pc_line") else None,
        val_line=val_line if plot_flags.get("val_line") else None,
    )


# ######################################################################################
@app.callback(
    Output("cycle-store", "data"),
    Input("raw-data-store", "data"),
    Input('final-mainseriesonly-store', 'data'),
    Input("base-str-input", "value"),
    Input("sum-first-n-base-input", "value"),
    Input("hike-threshold-input", "value"),
    Input("ease-threshold-input", "value"),
    State('general-store', 'data'),
    prevent_initial_call=False
)
def classify_and_store(stored_raw, stored_ser, base_str, sum_first_n_base, hike_threshold, ease_threshold, general_store):
    if general_store is not None:
        comdty,str_name, str_num,lookback_prd= general_store[0], general_store[1],general_store[2],general_store[3]
        if comdty not in {"SR3", "SO3", "ER", "SA3", "CRA", "ESTR"}:
            return None

    if not stored_raw or not stored_ser:
        return {}
    #print(base_str, sum_first_n_base, hike_threshold, ease_threshold)
    if any in {base_str, sum_first_n_base, hike_threshold, ease_threshold} is None:
        raise PreventUpdate
    if base_str not in {"Out", "S3", "S6", "S12", "L6", "L3"}:
        raise PreventUpdate
    if sum_first_n_base< 1:
        raise PreventUpdate
    
    sum_first_n_base= int(sum_first_n_base)
    hike_threshold= int(hike_threshold)
    ease_threshold= int(ease_threshold)

    series = pd.Series(
    data=stored_ser["values"],
    index=pd.to_datetime(stored_ser["index"], errors="coerce")
    )

    if series.empty:
        return {}
    comdty,str_name, str_num,lookback_prd= general_store[0], general_store[1],general_store[2],general_store[3]
    if not stored_raw or not stored_raw.get('data'):
        return warning_plot("no raw data dict found update_tab_2_2 "), warning_plot("no raw data dict found update_tab_2_3 ")
    
    raw_df = pd.DataFrame(
        data=stored_raw['data'],
        index=pd.to_datetime(stored_raw.get('index', None), errors='coerce', format='mixed'), # Convert back to DatetimeIndex
        columns=stored_raw.get('columns', None)
    )
    
    hike_cycle, ease_cycle, side_ways = classify_cycle(
        series= series,
        comdty= comdty,
        out_df= raw_df,
        lookback_prd= lookback_prd,
        base_str=base_str,
        sum_first_n_base=sum_first_n_base,
        hike_threshold=hike_threshold,
        dovish_threshold=ease_threshold,
    )
    #print(len( hike_cycle), len(ease_cycle), len(side_ways))
    # print(series)
    # print(round(series.iloc[0], 2))
    return {
        "latest": series.iloc[0],
        "hike": list(hike_cycle),
        "ease": list(ease_cycle),
        "sideways": list(side_ways)
    }


# # ----------------------------------------------------------------
# # CALLBACK: hike-KDE Plot (Tab 4 - # --------------------------------------------------------------
# # CALLBACK: ease-KDE Plot (Tab 5 # ------------------------------------------------------
# # CALLBACK: sideways-KDE Plot (Tab 6 # ------------------------------------------------------------
# # ----------------------------------------------------------------

@app.callback(
    [Output('hike-kde-plot', 'figure'),
    Output('ease-kde-plot', 'figure'),
    Output('side-kde-plot', 'figure')],
    Input("cycle-store", "data"),
    Input('kde-flags-shared', 'value'),

    Input('kde-val-line-shared', 'value'),
    Input('kde-pc-line-shared', 'value'),
    State('general-store', 'data'),
    prevent_initial_call=False
)
def update_kde_plot_tab4(cycle_store, kde_flags, val_line, pc_line, general_store):
    def warning_all(msg):
        fig = warning_plot(msg)
        return fig, fig, fig

    if general_store is not None:
        comdty,str_name, str_num,lookback_prd= general_store[0], general_store[1],general_store[2],general_store[3]
        if comdty not in {"SR3", "SO3", "ER", "SA3", "CRA", "ESTR"}:
            return warning_all(f"Not applicable for {comdty} commodity")


    # Build plot_flags
    plot_flags = {flag: (flag in kde_flags) for flag in [
        "Latest", "bb1", "bb2", 
         "med",  "pc_line", "val_line", "band68", "band95"
    ]}
    
    # Check for subseries (hike cycle)
    if cycle_store is None:
        return warning_all(f"No classification data available for {comdty} commodity")
    latest_val = cycle_store.get("latest", None)
    hike_series = pd.Series(cycle_store["hike"]) if "hike" in cycle_store else None
    ease_series = pd.Series(cycle_store["ease"]) if "ease" in cycle_store else None
    sideways_series = pd.Series(cycle_store["sideways"]) if "sideways" in cycle_store else None
    # Check for subseries (ease cycle)
    if hike_series is None:
        hike_fig= warning_plot("⚠ No 'Hike' cycle data available")
    if ease_series is None:
        ease_fig= warning_plot("⚠ No 'Ease' cycle data available")
    if sideways_series is None:
        sideways_fig= warning_plot("⚠ No 'Sideways' cycle data available")


    hike_title= f"{comdty}{str_name}({str_num}) in Hike Cycle- {len(hike_series) if (hike_series is not None) else 0} pts"
    ease_title= f"{comdty}{str_name}({str_num}) in Ease Cycle- {len(ease_series) if (ease_series is not None) else 0} pts"    
    sideways_title= f"{comdty}{str_name}({str_num}) in Sideways Cycle- {len(sideways_series) if (sideways_series is not None) else 0} pts"       
    
    hike_fig= plotted_sub_KDE( plot_flags=plot_flags, sub_series= hike_series, title= hike_title, cycle_name= "Hike",
        latest_val= latest_val,
        pc_line=pc_line if plot_flags.get("pc_line") else None,
        val_line=val_line if plot_flags.get("val_line") else None
    )
    ease_fig= plotted_sub_KDE( plot_flags=plot_flags, sub_series= ease_series, title= ease_title,cycle_name= "Ease",
        latest_val= latest_val,
        pc_line=pc_line if plot_flags.get("pc_line") else None,
        val_line=val_line if plot_flags.get("val_line") else None
    ) 
    sideways_fig= plotted_sub_KDE( plot_flags=plot_flags, sub_series= sideways_series,title= sideways_title, cycle_name= "Sideways",
        latest_val= latest_val,
        pc_line=pc_line if plot_flags.get("pc_line") else None,
        val_line=val_line if plot_flags.get("val_line") else None
    )
    return hike_fig, ease_fig, sideways_fig

# ############################################## tab 7 ############################################################################
#computed 3d df  storing in cache memory 
@cache.memoize()  
def cached_compute_3d_df( raw_df, local_win: int, curve_len: int):
    """
    A wrapper for compute_3d_structure that is memoized (cached).
    It takes a JSON-serializable dict and converts it to a DataFrame internally.
    """
    # This print statement will only execute when the function is not using a cached result
    print(f"Cache memo: Running computation for 3d df for win={local_win}, len={curve_len}...")
    
    # # Convert the dictionary from dcc.Store back into a DataFrame
    # raw_df = pd.DataFrame(
    #     data=stored_raw['data'],
    #     index=pd.to_datetime(stored_raw.get('index', None), errors='coerce', format='mixed'), # Convert back to DatetimeIndex
    #     columns=stored_raw.get('columns', None)
    # )
    # Call original, expensive function
    return compute_3d_structure(raw_df, local_win=local_win, curve_length=curve_len)



@app.callback(
    Output("tab7-buttons-store-price", "data"),
    [Input(btn_id, "n_clicks") for btn_id in matrix_buttons_price],
    State("tab7-buttons-store-price", "data"),
    prevent_initial_call=True
)
def toggle_buttons(*args):
    store = args[-1] or {}

    triggered_id = ctx.triggered_id
    if not triggered_id:
        return dash.no_update
    if triggered_id:
        current = store.get(triggered_id, False)
        # Create a new state dictionary, starting with all buttons as inactive
        new_store = {btn_id: False for btn_id in matrix_buttons_price}
        # If the button was not already active, set it to active.
        # If it was active, it will now be deselected (as per the new_store initialization).
        if not current:
            new_store[triggered_id] = True 
    return new_store


@app.callback(
    Output("tab7-buttons-store-color", "data"),
    [Input(btn_id, "n_clicks") for btn_id in matrix_buttons_color],
    State("tab7-buttons-store-color", "data"),
    prevent_initial_call=True
)
def toggle_buttons(*args):
    store = args[-1] or {}
    triggered_id = ctx.triggered_id
    if not triggered_id:
        return dash.no_update
    if triggered_id:
        current = store.get(triggered_id, False)
        store[triggered_id] = not current
    return store

@app.callback(
    [Output(btn_id, "className") for btn_id in matrix_buttons_price],
    Input("tab7-buttons-store-price", "data")
)
def update_classnames(store):
    return [get_button_class_tab7(store.get(btn_id, False)) for btn_id in matrix_buttons_price]

@app.callback(
    [Output(btn_id, "className") for btn_id in matrix_buttons_color],
    Input("tab7-buttons-store-color", "data")
)
def update_classnames(store):
    return [get_button_class_tab7(store.get(btn_id, False)) for btn_id in matrix_buttons_color]
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
    Output('heatmap-ready-signal', 'data'),
    Input('raw-data-store', 'data'),
    Input('dropdown-ratio', 'value'),
    Input('input-local-window', 'value'),
    Input('input-curve-length', 'value'),
    Input('tab7-buttons-store-price', 'data'),
    Input('tab7-buttons-store-color', 'data'),
    Input('tabs', 'value'),
    State('general-store', 'data'),
    prevent_initial_call=True
)
def update_tab_heatmap_basic(raw_data_dict,selected_ratio, local_win, curve_len, toggle_store_price, toggle_store_color, tab, general_store):
    if not raw_data_dict:
        return warning_plot("⚠ data not available (no stored data)"), time.time()

    if not selected_ratio:
        selected_ratio=  {"Out", "S3","S6","L3","L6"} # Return an empty figure
    
    if general_store is not None:
        comdty = general_store[0]
        if comdty in {"VIX", "meets", "FVS", "VIX-VOXX"}:
            selected_ratio = [index[i] for i in list(range(0, 4)) + list(range(28, 34))]
    
    if not raw_data_dict.get('data'):
        return {}
    
    raw_df = pd.DataFrame(
        data=raw_data_dict['data'],
        index=pd.to_datetime(raw_data_dict.get('index', None), errors='coerce', format='mixed'), # Convert back to DatetimeIndex
        columns=raw_data_dict.get('columns', None)
    )
    
    if raw_df is None:
        raise PreventUpdate  # or handle gracefully
    
    str_data_3d = cached_compute_3d_df(raw_df,  local_win, curve_len)
    filtered_3d_df = str_data_3d[str_data_3d.index.get_level_values('Structure').isin(selected_ratio)]

    latest_date =  filtered_3d_df.index.get_level_values("Date").unique()[0]
    # Slice the data to get the datasets for the heatmap layers.
    latest_df =  filtered_3d_df.loc[latest_date]
    risk_reward_df, risk_reward_diff_df, roll_down_df, roll_up_df = compute_risk_reward_roll_df(latest_df)
    percentile_df = compute_percentile_df( filtered_3d_df)
    zscore_df=    compute_zscore_df( filtered_3d_df)
    range_df= compute_range_df(filtered_3d_df)
    regime_df= classify_regime_in_series(filtered_3d_df)
    #print("pd", percentile_df)
    values_btn_fig_map = {
        "btn-price": lambda: generate_heatmap(1, latest_df),
        "btn-percentile": lambda: generate_heatmap(0, percentile_df),
        "btn-zscore": lambda: generate_heatmap(1, zscore_df),
        "btn-riskrewarddiff": lambda: generate_heatmap(1, risk_reward_diff_df),
        "btn-riskreward": lambda: generate_heatmap(1, risk_reward_df),
        "btn-rolldown": lambda: generate_heatmap(1, roll_down_df),
        "btn-rollup": lambda: generate_heatmap(1, roll_up_df),
        "btn-range": lambda: generate_heatmap(1, range_df),
        "btn-trend": lambda: generate_heatmap(1, regime_df),
    }

    heatmap = None
    for btn_id, generate_func in values_btn_fig_map.items():
        if toggle_store_price.get(btn_id, False):
            heatmap= generate_func() 
            break

    heatmap = hovertemplate_heatmap(heatmap, latest_df, roll_down_df, roll_up_df, percentile_df)   
    colors_btn_fig_map = {
        #"btn-price_2": lambda: color_heatmap(heatmap, 1, latest_df),
        "btn-percentile_2": lambda: color_heatmap(heatmap, 0, percentile_df),
        "btn-zscore_2": lambda: color_heatmap(heatmap, 1, zscore_df),
        "btn-riskrewarddiff_2": lambda: color_heatmap( heatmap, 1, risk_reward_diff_df),
        "btn-riskreward_2": lambda: color_heatmap(heatmap, 1, risk_reward_df),
        "btn-rolldown_2": lambda: color_heatmap(heatmap, 1, roll_down_df),
        "btn-rollup_2": lambda: color_heatmap(heatmap, 1, roll_up_df),
        "btn-range": lambda: generate_heatmap(1, range_df),
        #"btn-trend": lambda: generate_heatmap(1, trend_df),

    }
    filter_btn_fig_map = {
        "btn-rank595_2": lambda: filter_grey(heatmap, 595, percentile_df), # Assuming these use the same data
        "btn-rank1090_2": lambda: filter_grey(heatmap, 1090, percentile_df),
        # "btn-riskrewarddiff_2": lambda: color_heatmap( heatmap, 1, risk_reward_diff_df),
        # "btn-riskreward_2": lambda: color_heatmap(heatmap, 1, risk_reward_df),
        # "btn-rolldown_2": lambda: color_heatmap(heatmap, 1, roll_down_df),
    }
   
    
    #If no value selected, create fallback base heatmap (with empty values)
    if heatmap is None:
        fallback_df = latest_df  # or any other safe default
        heatmap = create_blank_heatmap(fallback_df)

    for btn_id, color_fn in colors_btn_fig_map.items():
        if toggle_store_color.get(btn_id, False):
            return color_fn() , time.time()
    
    for btn_id, grey_fn in filter_btn_fig_map.items():
        if toggle_store_color.get(btn_id, False):
            return grey_fn() , time.time()


    # If no button is active, return a warning message.
    return heatmap, time.time() 


    

#################### side detail panel ###########
# Inside the display_cell_details callback...
@app.callback(
    Output('heatmap-details-panel', 'children'),
    Output('heatmap-details-panel', 'style'),
    Input('heatmap-matrix', 'clickData'),
    State('raw-data-store', 'data'),
    Input('dropdown-ratio', 'value'),
    State('input-local-window', 'value'),
    State('input-curve-length', 'value'),
    prevent_initial_call=True
)
def display_cell_details(click_data, raw_data_dict ,selected_ratio, local_win, curve_len):
    if click_data is None:
        return dash.no_update, dash.no_update
    
    if not selected_ratio:
        selected_ratio=  {"Out", "S3","S6","L3","L6"} # Return an empty figure
    # --- 1. Extract Info from the Clicked Cell ---
    point = click_data['points'][0]
    x_val, y_val = point['x'], point['y']
    
    
    if not raw_data_dict.get('data'):
        return {}
    
    raw_df = pd.DataFrame(
        data=raw_data_dict['data'],
        index=pd.to_datetime(raw_data_dict.get('index', None), errors='coerce', format='mixed'), # Convert back to DatetimeIndex
        columns=raw_data_dict.get('columns', None)
    )
    
    if raw_df is None:
        raise PreventUpdate  # or handle gracefully

    str_data_3d = cached_compute_3d_df(raw_df, local_win, curve_len)
    filtered_3d_df = str_data_3d[str_data_3d.index.get_level_values('Structure').isin(selected_ratio)]
    clicked_series=  filtered_3d_df.loc[(slice(None), x_val, y_val)]
    prev_val, next_val= get_adjacent_values( filtered_3d_df,  x_val, y_val)
    #print(clicked_series)
    panel_content = generate_heatmap_detail_panel (clicked_series, x_val, y_val, prev_val, next_val)
    return panel_content, {'display': 'block'}

#### hiding again on clicking cross #### 
@app.callback(
    Output('heatmap-details-panel', 'style', allow_duplicate=True),
    Input('details-panel-close-btn', 'n_clicks'),
    prevent_initial_call=True
)
def hide_details_panel(n_clicks):
    # It prevents the callback from running if n_clicks is None or 0.
    if not n_clicks:
        raise PreventUpdate
    return {'display': 'none'}


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



# Function to pick port
def get_free_port(preferred_port, fallback_port):
    """Try preferred_port, if busy then use fallback_port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", preferred_port)) != 0:
            return preferred_port  # free
        else:
            return fallback_port   # fallback
# ------------------------------------------------
# MAIN
# ------------------------------------------------
if __name__ == '__main__':
    #app.run(debug= False, host='0.0.0.0', port=8050) #for live hosted version  https://million-dollar.onrender.com/
    #app.run(debug= True) #self
    app.run(debug=False, port=get_free_port(8050, 8060))  #for download 