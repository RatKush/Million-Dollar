# A Dash app to explore structure curve data: Curve view, chart and KDE analysis
import time
from typing import Optional, Union, Dict, Any
import logging
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, ctx, callback, no_update
from dash.dependencies import ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from flask_caching import Cache
import plotly.graph_objects as go
import hashlib

# 1. THE ENTERPRISE SCRIPT for adding sprakline in table
external_scripts = ["https://cdn.jsdelivr.net/npm/ag-grid-enterprise/dist/ag-grid-enterprise.min.js"]

# 2. tab wise imports
from str_cal import  process_raw_data, index, get_ratio, fetch_rates_cycle,fn_main_series_only, process_structure_data, serialize_dataframe, serialize_series
from tab0_header import create_header_component, get_free_port, extract_comdty, get_excel_files
from tab1_curve import  create_tab1_view,  generate_curve_plot, table_populating_1_2
from tab2_curve import (
    tab_2_2_2_3_button_ids, create_tab2_view,get_button_class, compute_correlation_parameters,plot_single_structure,cal_sum_of_eases_hikes, cal_sum_of_same_sign_meets,
    Out_tab2_2, S12_tab2_2, L6_tab2_2, add_chart_2_2, plot_chart_2_2, add_chart_2_3, plot_chart_2_3
)
from tab3456_kde_help import plot_main_kde, classify_cycle, plotted_sub_KDE, create_kde_tab, kde_control_wrapper
from tab7_matrix import (
    get_button_class_tab7, generate_heatmap, color_heatmap,
    create_blank_heatmap, compute_3d_structure, compute_percentile_df,compute_zscore_df, compute_range_df,classify_regime_in_series,
    compute_risk_reward_roll_df, hovertemplate_heatmap, generate_heatmap_detail_panel,
    get_adjacent_values, filter_grey, matrix_buttons_price, matrix_buttons_color, create_tab7_view
) 
from tab9_footer import footer_component, send_feedback_email

# default variables
DEFAULT_CURVE_LENGTH = 20
DEFAULT_LOOKBACK = 250
MIN_DEFAULT_LOOKBACK = 63  # Minimum lookback period
DEFAULT_WINDOW = 21
DEFAULT_OUTLIER_K = 2.5
# Get available Excel files and setup dropdown options
SUPPORTED_EXCEL_EXTENSIONS = ('.xlsx', '.xlsm', '.csv')
DEFAULT_FILES = ["SR3_ED_GEN.xlsm", "SR3.xlsx"]
DEFAULT_STR_NAME= "L6"
DEFAULT_STR_NO=8
# Application configuration
APP_CONFIG = {
    'title': "Million Dollar",
    'theme': dbc.themes.CYBORG,
    'assets_folder': 'assets',
    'suppress_callback_exceptions': True,
    'cache_type': 'simple'  # Use 'filesystem' or 'redis' for production
}

# -------------------------------------------------------------------------------------------------------------------------------------------
# DASH APP INITIALIZATION
# ----------------------------------------------------------------------------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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

excel_files = get_excel_files(SUPPORTED_EXCEL_EXTENSIONS)
filename_options = [{'label': filename, 'value': filename} for filename in excel_files]
default_filename, default_comdty = get_default_filename_comdty(excel_files)

app, cache = initialize_app() # Initialize Dash application and cache
##################################################### app layout ########################################################################################
app.layout = dbc.Container([
    create_header_component(filename_options, default_filename, default_comdty, DEFAULT_CURVE_LENGTH, DEFAULT_LOOKBACK, index),
####################################################################### tab 1 ###################################################
    dcc.Tabs(id="tabs", value='tab1', children=[
        create_tab1_view(),
############################################################# tab 7 ################################################################        
        create_tab7_view(DEFAULT_CURVE_LENGTH),
###################################################  tab 2 ##############################################################################
        create_tab2_view(),
######################################################## tab3 #############################################################
        create_kde_tab("KDE", "tab3", "loading-kde", 'kde-plot'),
        create_kde_tab("KDE (Hike Cycle)", 'tab4', "loading-hike-kde", 'hike-kde-plot'),
        create_kde_tab("KDE (Ease Cycle)", 'tab5', "ease-loading-kde", 'ease-kde-plot'),
        create_kde_tab("KDE (Side Ways)", 'tab6', "side-loading-kde", 'side-kde-plot'),   
################################################################# tab 8 ###################################################
        dcc.Tab(label='Snapshot', value='tab8',
            style={"height": "42px","borderRadius": "8px 8px 0 0","padding": "8px 16px","marginRight": "4px","backgroundColor": "#2b2e35","color":  "#c0c4cc","fontWeight": "500","border": "1px solid #3a3f4b","borderBottom": "none","transition": "background-color 0.3s, color 0.3s"
            },
            selected_style={"height": "45px","borderRadius": "8px 8px 0 0","padding": "8px 16px","backgroundColor": "#1f2128","color": "#ffffff","fontWeight": "600","border": "1px solid #5e636e","borderBottom": "none","boxShadow": "0px -2px 6px rgba(0, 0, 0, 0.4)"
            },
        )
    ]),  # ← close Tabs here
#############################################################################################################################################
    kde_control_wrapper,
    #kde_checklist,
    html.Hr(),
    footer_component, 

    dcc.Store(id='raw-data-store', storage_type='session'),
    dcc.Store(id='general-store', data=[default_comdty, DEFAULT_STR_NAME, DEFAULT_STR_NO, DEFAULT_LOOKBACK], storage_type='session'),
    #dcc.Store(id="dt_latest", storage_type='session'),
    dcc.Store(id='structure-data-store', storage_type='session'),
    dcc.Store(id='final-mainseriesonly-store', storage_type='session'),
    dcc.Store(id="shared-xrange_2_1_2_2"),   # hidden storage for sync
    dcc.Store(id='cycle-store',storage_type='session' ),#persistence=True
    dcc.Store(id='user-matrix_ratio-preference', storage_type='local'),
    dcc.Store(id="colorscale-preference", data={"selected_color_scale": "BG"},  storage_type='local')

], fluid=True)  # ← close Container here


# ---------------------------------------------------------------------------------------------------
# CALLBACK: Load & Process raw data (outright) and Structure Data df and interested Series
# ------------------------------------------------------------------------------------------------------
#setting lookback period
@callback(
    Output('lookback_prd', 'value'),
    Input('lookback_prd', 'search_value'),
    State('lookback_prd', 'value'),
    prevent_initial_call=False
)
def set_custom_lookback(search_value, current_value):
    """
    Allows both selecting from dropdown and typing custom lookback days.
    If user types numeric input, use it directly.
    """
    if search_value:
        sv = search_value.strip() # ✅ numeric check
        if sv.isdigit():
            val = int(sv)
            if val >= 63:
                return val
            else:
                return MIN_DEFAULT_LOOKBACK
        else:
            # non-numeric input → reset to default
            return DEFAULT_LOOKBACK
    # no search_value (user picked from list or cleared)
    return current_value or DEFAULT_LOOKBACK


@callback(
    Output('general-store', 'data'),
    [Input('filename', 'value'),
    Input('str_name', 'value'),
    Input('str_number', 'value'),
    Input('lookback_prd', 'value'),
    Input('load-btn', 'n_clicks')],
    prevent_initial_call= False)
def general_info(filename, str_name, str_num, lookback_prd, n_clicks):
    if not filename or not str_name or not  str_num or not  lookback_prd :
        raise PreventUpdate # don’t update store if no file chosen

    comdty = extract_comdty(filename)
    str_name = str(str_name).strip() if str_name else None
    str_num = int(str_num) if str_num and str(str_num).isdigit() else None
    lookback_prd = int(lookback_prd) if lookback_prd and str(lookback_prd).isdigit() else None
    #print(str_name)
    # Return as list (JSON serializable)
    return [comdty, str_name, str_num, lookback_prd]


######################## populatintg comodity #################################################
@callback(
    Output('comdty', 'value'),
    [Input('general-store', 'data'),
    Input('load-btn', 'n_clicks')],
    prevent_initial_call=False,
)
def update_comdty_input(general_data: list, n_clicks) -> str:
    """Updates the commodity input field based on the stored commodity data."""
    if not general_data or len(general_data) < 1:
        return ""
    return str(general_data[0])   # first element = comdty

################################################ extracting raw data i.e outright ################################
@callback(
    [Output('raw-data-store', 'data'),
    Output('dt_latest', 'value')],
    [Input('filename', 'value'),
     Input('lookback_prd', 'value'),
     Input('load-btn', 'n_clicks')],
     prevent_initial_call=False,
)
def extract_raw_data(filename: str, lookback_prd: Union[str, int], n_clicks) -> Dict[str, Any]:
    """CORRECTED: Extract raw data callback - simplified validation"""
    # Basic validation - return empty if invalid inputs
    if not filename or not lookback_prd:
        raise PreventUpdate
    
    try:
        lookback_prd_int = int(lookback_prd)
        if lookback_prd_int <= 0:
            return {}, None
        
        # Load and process data - FIXED: now returns tuple
        raw_df = process_raw_data(filepath=filename, lookback_prd=lookback_prd_int)
        if raw_df.empty:
            return {}, None
        
        # Serialize the raw data for storage
        try:
            ts = pd.to_datetime(raw_df.index[0], errors='coerce')
            latest_date = ts.strftime("%d-%m-%y") if pd.notnull(ts) else None
        except Exception as e:
            logging.warning(f"Could not parse latest date: {e}")
            latest_date = None

        serialized_raw_data = serialize_dataframe(raw_df)
        return serialized_raw_data, latest_date
        
    except Exception as e:
        logging.error(f"Error in extract_raw_data_callback for file {filename}: {e}")
        return {}, None


############################ ONLY MAIN SERIES cal of length lookback prd ######################################################################
@callback(
    Output('final-mainseriesonly-store', 'data'),
    [Input('raw-data-store', 'data'),
    State('general-store', 'data'),
    Input('str_name', 'value'),
    Input('str_number', 'value'),
    Input('lookback_prd', 'value')],
    prevent_initial_call=False
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
        return serialize_series( fn_main_series_only(raw_df,str_name,str_number_int, general_store[0],lookback_int, DEFAULT_WINDOW, DEFAULT_OUTLIER_K))
        
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

################################################## str_df store ############################################################################################
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

################################################## plotting 1.1 ############################################################################################   
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
            DEFAULT_WINDOW=DEFAULT_WINDOW, 
            DEFAULT_OUTLIER_K=DEFAULT_OUTLIER_K
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

# ##################### tab 2_2 ######################################################################################################################
# ########################################### tab_2_3 ###################################################################################################

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
    #print(str_name)
    trace_config = {
        "btn-nth_out": {
            "func": Out_tab2_2,
            "args": (raw_df,comdty, str_num, lookback_prd, DEFAULT_WINDOW, DEFAULT_OUTLIER_K),
            "legend": "nth Out",
            "color": "#f58231" # Orange
        },
        "btn-mid_out": {
            "func": Out_tab2_2,
            "args": (raw_df, comdty, str_num + int(len(get_ratio(str_name)) / 2), lookback_prd, DEFAULT_WINDOW, DEFAULT_OUTLIER_K),
            "legend": "Mid Out",
            "color": "#ffe119" # Bright Yellow
        },
        "btn-1sts12": {
            "func": S12_tab2_2,
            "args": (raw_df, 1, lookback_prd, DEFAULT_WINDOW,DEFAULT_OUTLIER_K),
            "legend": "1st S12",
            "color": "#006666" # Cyan
        },
        "btn-nths12": {
            "func": S12_tab2_2,
            "args": (raw_df, str_num, lookback_prd, DEFAULT_WINDOW,DEFAULT_OUTLIER_K),
            "legend": "nth S12",
            "color": "#3cb44b" # Strong Green
        },
        "btn-12ths12": {
            "func": S12_tab2_2,
            "args": (raw_df, 12, lookback_prd, DEFAULT_WINDOW,DEFAULT_OUTLIER_K),
            "legend": "12th S12",
            "color": "#f032e6" # Magenta
        },
        "btn-nthl6": {
            "func": L6_tab2_2,
            "args": (raw_df, str_num, lookback_prd, DEFAULT_WINDOW,DEFAULT_OUTLIER_K ),
            "legend": "nth L6",
            "color": "rgb(152,78,163)"
        }
    }

    # --- Handle Special Cases & One-Offs ---

    # 1. Sum of eases/hikes
    if toggle_store.get("btn-ease_hike"):
        if comdty == "MEETS":
            series_data = cal_sum_of_same_sign_meets(raw_df, comdty, lookback_prd, DEFAULT_WINDOW= DEFAULT_WINDOW, DEFAULT_OUTLIER_K= DEFAULT_OUTLIER_K)
        elif comdty in {"SR3", "ER", "SO3", "SA3", "CRA", "ER3"}:
            series_data = cal_sum_of_eases_hikes(raw_df, comdty, lookback_prd, DEFAULT_WINDOW=DEFAULT_WINDOW, DEFAULT_OUTLIER_K= DEFAULT_OUTLIER_K)
        else:
            series_data = pd.Series(dtype='float64')
        
        add_chart_2_3(fig2_3, chart2_1_series, series_data, legend="sum of eases/ hikes", color="#4363d8")
        corr = compute_correlation_parameters(chart2_1_series, series_data)
        add_chart_2_2(fig2_2, series_data, corr, legend="sum of eases/ hikes", color="#4363d8")

    # 2. Treasury rates (fetch data only once)
    treasury_buttons = {"btn-effr", "btn-2yr", "btn-5yr", "btn-10yr", "btn-2y10y"}
    if any(toggle_store.get(btn) for btn in treasury_buttons):
        df_rates = fetch_rates_cycle(lookback_prd, filepath="SR3_ED_GEN.xlsm", sheetname="treasuries rates")
        
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
                    corr = {'pearson':None, 'mean_rolling_correlation': None, 'distance_correlation': None}
                else:
                    corr = compute_correlation_parameters(chart2_1_series, series_data)
                add_chart_2_2(fig2_2, series_data, corr, legend=params["legend"], color=params["color"])

    # --- Process Standard Traces from Config ---
    for btn, config in trace_config.items():
        if toggle_store.get(btn):
            series_data = config["func"](*config["args"])
            add_chart_2_3(fig2_3, chart2_1_series, series_data, legend=config["legend"], color=config["color"])
            corr = compute_correlation_parameters(chart2_1_series, series_data )
            add_chart_2_2(fig2_2, series_data, corr, legend=config["legend"], color=config["color"])

    return fig2_2, fig2_3

# # ---------------------------------------------------------------------------------------------------------
# # CALLBACK:  shared KDE Input Toggle tab3 | tab4 | tab5 | tab6
# # ------------------------------------------------------------------------------------------------------------

# #rendering control panel in tab 3 to tab6
@app.callback(
    Output("kde-flags-shared-wrapper", "style"),
    Input("tabs", "value"),
    prevent_initial_call=False
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
    prevent_initial_call=True
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


# ###################################################################################### cycle classification fo tab 4,5,6, #############################################
@app.callback(
    Output("cycle-store", "data"),
    Input("raw-data-store", "data"),
    Input('final-mainseriesonly-store', 'data'),
    Input("base-str-input", "value"),
    Input("sum-first-n-base-input", "value"),
    Input("hike-threshold-input", "value"),
    Input("ease-threshold-input", "value"),
    State('general-store', 'data'),
    prevent_initial_call=True
)
def classify_and_store(stored_raw, stored_ser, base_str, sum_first_n_base, hike_threshold, ease_threshold, general_store):
    if base_str is None or sum_first_n_base is None or hike_threshold is None or ease_threshold is None:
        raise PreventUpdate

    if general_store is not None:
        comdty,str_name, str_num,lookback_prd= general_store[0], general_store[1],general_store[2],general_store[3]
        if comdty not in {"SR3", "SO3", "ER", "SA3", "CRA",  "ER3"}:
            return None

    if not stored_raw or not stored_ser:
        return {}
    #print(base_str, sum_first_n_base, hike_threshold, ease_threshold)
    if any in {base_str, sum_first_n_base, hike_threshold, ease_threshold} is None:
        raise PreventUpdate
    if base_str not in {"OUT", "S3", "S6", "S12", "L6", "L3"}:
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
    prevent_initial_call=True
)
def update_kde_plot_tab4(cycle_store, kde_flags, val_line, pc_line, general_store):
    def warning_all(msg):
        fig = warning_plot(msg)
        return fig, fig, fig

    if general_store is not None:
        comdty,str_name, str_num,lookback_prd= general_store[0], general_store[1],general_store[2],general_store[3]
        if comdty not in {"SR3", "SO3", "ER", "SA3", "CRA",  "ER3"}:
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


    hike_title= f"{comdty} {str_name}({str_num}) in Hike Cycle- {len(hike_series) if (hike_series is not None) else 0} pts"
    ease_title= f"{comdty} {str_name}({str_num}) in Ease Cycle- {len(ease_series) if (ease_series is not None) else 0} pts"    
    sideways_title= f"{comdty} {str_name}({str_num}) in Sideways Cycle- {len(sideways_series) if (sideways_series is not None) else 0} pts"       
    
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
def cached_compute_3d_df(comdty, df_hash: str, local_win: int, curve_len: int, raw_df):
    @cache.memoize()
    def _inner(df_hash, local_win, curve_len, comdty):
        print(f"Cache miss → computing 3D df (win={local_win}, len={curve_len})")
        return compute_3d_structure(comdty, raw_df, local_win=local_win, curve_length=curve_len)
    return _inner( df_hash, local_win, curve_len, comdty)



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
    
############################### color scale switching stsrts #########################################################

@callback(
    Output("colorscale-menu", "style"),
    Output("color-scale-choice", "value"),
    Output("colorscale-preference", "data"),
    Input("color-title", "n_clicks"),
    Input("color-scale-choice", "value"),
    State("colorscale-menu", "style"),
    State("colorscale-preference", "data"),
    prevent_initial_call=True
)
def handle_colorscale_menu(n_clicks, selected_value, current_style, stored_data):
    """
    Opens menu on single click and auto-closes whenever the user clicks a radio button,
    even if the selection is the same as before.
    """
    stored_data = stored_data or {}
    new_style = current_style.copy()

    # Initialize static attributes to track actual user selection
    if not hasattr(handle_colorscale_menu, "prev_value"):
        handle_colorscale_menu.prev_value = stored_data.get("selected_color_scale", "BG")

    # -------------------------
    # 1️⃣ Toggle menu on single click of Colors header
    # -------------------------
    if n_clicks is not None:
        current_display = current_style.get("display", "none")
        new_display = "block" if current_display == "none" else "none"
        new_style["display"] = new_display
        stored_data["menu_visible"] = new_display == "block"

    # -------------------------
    # 2️⃣ Close menu only on actual user click of radio button
    # -------------------------
    # Only react if the value has changed or user clicks the same value again
    if selected_value is not None and selected_value != handle_colorscale_menu.prev_value:
        stored_data["selected_color_scale"] = selected_value
        handle_colorscale_menu.prev_value = selected_value
        new_style["display"] = "none"
        stored_data["menu_visible"] = False

    # -------------------------
    # 3️⃣ Restore the radio button value
    # -------------------------
    restored_value = stored_data.get("selected_color_scale", "BG")

    return new_style, restored_value, stored_data

############################## color scale switching  ends #########################################################
############################## user matrix default ratio remember #########################################################
@app.callback(
    Output('dropdown-ratio', 'value'),
    Output('user-matrix_ratio-preference', 'data'),
    Input('dropdown-ratio', 'value'),
    #Input('dropdown-commodity', 'value'),
    State('user-matrix_ratio-preference', 'data'),
    prevent_initial_call=False
)
def sync_ratio_preferences(selected_ratios, stored_data):
    # Ensure the store is initialized
    if stored_data is None:
        return selected_ratios, selected_ratios

    trigger = ctx.triggered_id
     # ---- Case 1: App startup or reload ----
    if trigger is None:# Restore saved value from store
        return stored_data, stored_data

    # ---- Case 2: User changed ratios manually ----
    if trigger == 'dropdown-ratio': # Update store to match latest selection
        return selected_ratios, selected_ratios
    # Case 3: No relevant trigger
    return no_update, stored_data
############################## user matrix default ratio remember ends #########################################################
@app.callback(
    Output('heatmap-matrix', 'figure'),
    Output('heatmap-ready-signal', 'data'),
    Input('raw-data-store', 'data'),
    Input('dropdown-ratio', 'value'),
    Input('input-local-window', 'value'),
    Input('tab7-buttons-store-price', 'data'),
    Input('tab7-buttons-store-color', 'data'),
    Input('tabs', 'value'),
    Input('curve_length', 'value'),
    State('general-store', 'data'),
    State('colorscale-preference', 'data'), 
    prevent_initial_call=True
)
def update_tab7_heatmap_basic(raw_data_dict,selected_ratio, local_win, toggle_store_price, toggle_store_color, tab, curve_len, general_store, stored_color_data):
    if not raw_data_dict:
        return warning_plot("⚠ data not available (no stored data)"), time.time()

    if not selected_ratio:
        selected_ratio=  ["OUT", "S3","S6","L3","L6"] # Return an empty figure

    if general_store is not None:
        comdty = general_store[0]
        if comdty in {"VIX", "MEETS", "FVS", "VIX-VOX", "SZI0"}:
            selected_ratio =["OUT", "S3", "S6", "L3","1X Out- 2X O(n+1)", "2X Out- 1X O(n+1)", "2X Out- 3X O(n+1)", "3X Out- 2X O(n+1)", "1X S1- 2X S1(n+1)", "2X S1n- 1X S1(n+1)", "2X S1- 3X S1(n+1)", "3X S1- 2X S1(n+1)"]

    if curve_len is None or (isinstance(curve_len, str) and not curve_len.isdigit()) or (isinstance(curve_len, str) and int(curve_len) <= 0):
        curve_len= DEFAULT_CURVE_LENGTH
        print("Invalid curve_len update_tab_heatmap_basic")
    else:
        curve_len= curve_len


    if not raw_data_dict.get('data'):
        return {}
    
    raw_df = pd.DataFrame(
        data=raw_data_dict['data'],
        index=pd.to_datetime(raw_data_dict.get('index', None), errors='coerce', format='mixed'), # Convert back to DatetimeIndex
        columns=raw_data_dict.get('columns', None)
    )
    
    if raw_df is None or raw_df.empty:
        raise PreventUpdate  # or handle gracefully
    
    

    # inline hashing try quick hash
        # --- 2. Create quick hash AFTER DataFrame exists ---
    try:
        first_row = raw_df.iloc[0].to_numpy().tobytes() if len(raw_df) > 0 else b''
        last_row = raw_df.iloc[-1].to_numpy().tobytes() if len(raw_df) > 0 else b''
    except Exception:
        first_row = str(raw_df.iloc[0].tolist()).encode() if len(raw_df) > 0 else b''
        last_row= str(raw_df.iloc[-1].tolist()).encode() if len(raw_df) > 0 else b''

    meta = f"{raw_df.shape}".encode()
    df_quick_hash = hashlib.md5(first_row + last_row + meta).hexdigest()

    str_data_3d = cached_compute_3d_df(comdty, df_quick_hash, local_win, curve_len, raw_df)

    if not isinstance(str_data_3d.index, pd.MultiIndex) or "Structure" not in str_data_3d.index.names:
        print("⚠ Unexpected structure in cached_compute_3d_df output")
        return warning_plot("⚠ invalid STR data format"), time.time()
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
    # color_pref
    color_key = stored_color_data or {}
    color_pref = color_key.get("selected_color_scale", "BG")  # default to BG
    values_btn_fig_map = {
        "btn-price": lambda: generate_heatmap(1, latest_df, color_pref),
        "btn-percentile": lambda: generate_heatmap(0, percentile_df,color_pref),
        "btn-zscore": lambda: generate_heatmap(1, zscore_df,color_pref),
        "btn-riskrewarddiff": lambda: generate_heatmap(1, risk_reward_diff_df,color_pref),
        "btn-riskreward": lambda: generate_heatmap(1, risk_reward_df,color_pref),
        "btn-rolldown": lambda: generate_heatmap(1, roll_down_df, color_pref),
        "btn-rollup": lambda: generate_heatmap(1, roll_up_df, color_pref),
        "btn-range": lambda: generate_heatmap(1, range_df, color_pref),
        "btn-trend": lambda: generate_heatmap(1, regime_df, color_pref),
    }

    heatmap = None
    for btn_id, generate_func in values_btn_fig_map.items():
        if toggle_store_price.get(btn_id, False):
            heatmap= generate_func() 
            break

    heatmap = hovertemplate_heatmap(heatmap, latest_df, roll_down_df, roll_up_df, percentile_df)   
    colors_btn_fig_map = {
        #"btn-price_2": lambda: color_heatmap(heatmap, 1, latest_df),
        "btn-percentile_2": lambda: color_heatmap(heatmap, 0, percentile_df, color_pref),
        "btn-zscore_2": lambda: color_heatmap(heatmap, 0, zscore_df, color_pref),
        "btn-riskrewarddiff_2": lambda: color_heatmap( heatmap, 1, risk_reward_diff_df, color_pref),
        "btn-riskreward_2": lambda: color_heatmap(heatmap, 1, risk_reward_df, color_pref),
        "btn-rolldown_2": lambda: color_heatmap(heatmap, 1, roll_down_df, color_pref),
        "btn-rollup_2": lambda: color_heatmap(heatmap, 1, roll_up_df, color_pref),
        "btn-range": lambda: generate_heatmap(1, range_df, color_pref),
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

@app.callback(
    Output('heatmap-matrix', 'clickData'),
    Input('raw-data-store', 'data'),
    prevent_initial_call=True
)
def clear_click_data_on_dataset_change(_):
    return  None
# Inside the display_cell_details callback...
@app.callback(
    Output('heatmap-details-panel', 'children'),
    Output('heatmap-details-panel', 'style'),
    Input('heatmap-matrix', 'clickData'),
    Input('raw-data-store', 'data'),
    Input('dropdown-ratio', 'value'),
    Input('curve_length', 'value'),
    State('input-local-window', 'value'),
    State('general-store', 'data'),
    prevent_initial_call=True
)
def display_cell_details(click_data, raw_data_dict ,selected_ratio,curve_len, local_win, general_store):
    if click_data is None:
        return dash.no_update, dash.no_update
    
    if not selected_ratio:
        selected_ratio=  {"Out", "S3","S6","L3","L6"} # Return an empty figure

    if general_store is not None:
        comdty = general_store[0]
        if comdty in {"VIX", "MEETS", "FVS", "VIX-VOX", "SZI0"}:
            selected_ratio = ["OUT", "S3", "S6", "L3","1X Out- 2X O(n+1)", "2X Out- 1X O(n+1)", "2X Out- 3X O(n+1)", "3X Out- 2X O(n+1)", "1X S1- 2X S1(n+1)", "2X S1n- 1X S1(n+1)", "2X S1- 3X S1(n+1)", "3X S1- 2X S1(n+1)"]

    if curve_len is None or (isinstance(curve_len, str) and not curve_len.isdigit()) or (isinstance(curve_len, str) and int(curve_len) <= 0):
        curve_len= DEFAULT_CURVE_LENGTH
        print("Invalid curve_len in display_cell_details")
    else:
        curve_len= DEFAULT_CURVE_LENGTH
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

    try:
        first_row = raw_df.iloc[0].to_numpy().tobytes() if len(raw_df) > 0 else b''
        last_row = raw_df.iloc[-1].to_numpy().tobytes() if len(raw_df) > 0 else b''
    except Exception:
        first_row = str(raw_df.iloc[0].tolist()).encode() if len(raw_df) > 0 else b''
        last_row= str(raw_df.iloc[-1].tolist()).encode() if len(raw_df) > 0 else b''

    meta = f"{raw_df.shape}".encode()
    df_quick_hash = hashlib.md5(first_row + last_row + meta).hexdigest()

    str_data_3d = cached_compute_3d_df(comdty, df_quick_hash, local_win, curve_len, raw_df)
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

# ------------------------------------------------
# MAIN
# ------------------------------------------------
if __name__ == '__main__':
    app.run(debug= False, host='0.0.0.0', port=8050) #for live hosted version  https://million-dollar.onrender.com/
    #app.run(debug= True) #self
    #app.run(debug=False, port=get_free_port(8050, 8060))  #for download 
