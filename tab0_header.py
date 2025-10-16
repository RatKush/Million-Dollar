from dash import dcc, html
import dash_bootstrap_components as dbc
import socket
import difflib
from pathlib import Path
import os
lookback_options=[
    {'label': '3 Mo (63)', 'value': 63},
    {'label': '6 Mo (125)', 'value': 125},
    {'label': '1 Yr (250)', 'value': 250},
    {'label': '2 Yrs (500)', 'value': 500},
    {'label': '5 Yrs (1250)', 'value': 1250},
    {'label': '10 Yrs (2500)', 'value': 2500},
    {'label': '15 Yrs (3750)', 'value': 3750},
    {'label': '20 Yrs (5000)', 'value': 5000},
    {'label': 'All', 'value': 10000},
    {'label': '3 Yr (750)', 'value': 750},
    {'label': '4 Yrs (1000)', 'value': 1000},
    {'label': '8 Yrs (2000)', 'value': 2000},
    {'label': '12 Yrs (3000)', 'value': 3000},

]
def create_header_component(filename_options, default_filename, default_comdty, DEFAULT_CURVE_LENGTH, DEFAULT_LOOKBACK, index):
    header_component=dbc.Row([
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
            html.Label("Commodity",style={"color": "#c0c4cc", "fontWeight": "500",  "fontSize": "14px",   "marginBottom": "4px" }),
            dcc.Loading(
                dcc.Input(id='comdty', type='text', value= default_comdty, disabled=True, className='form-control'),
            type= 'circle'
            )
        ]),
        dbc.Col([
            html.Label("Latest date",style={"color": "#c0c4cc", "fontWeight": "500",  "fontSize": "14px",   "marginBottom": "4px" }),
            dcc.Loading(
                dcc.Input(id='dt_latest', type='text', value= None, disabled=True, className='form-control'),
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
            html.Label("Structure Number", style={"color": "#c0c4cc", "fontWeight": "500",  "fontSize": "14px",   "marginBottom": "4px" }),
            dcc.Input(id='str_number', type='number', value=8, min=1, className='form-control')
        ]),
        dbc.Col([html.Label("Lookback Period",style={"color": "#c0c4cc","fontWeight": "500","fontSize": "14px","marginBottom": "4px"}),
            dcc.Dropdown(
                id='lookback_prd',
                options= lookback_options,
                value=DEFAULT_LOOKBACK,
                searchable=True,      # allows user to type custom
                clearable=False,       # optional
                placeholder="Select or type days...",
                className='form-control',   # ✅ match existing header styling
            )
        ]),
        dbc.Col([
            html.Label(" "),
            dbc.Button("Load", id='load-btn', color='primary', className='mt-4')
        ])
    ], className='mb-4')
    
    return header_component



# Commodity matching configuration
COMMODITY_MATCH_POOL = [
    "SR3_ED_GEN", "SR3_ED", "sr3", "sr1", "so3", "er", "er3","ER_GEN", "corra", "szi0", 
    "meeting", "meet", "sonia", "SO3_GEN", "sofr", "euribor", "meetings", 
    "sa3", "saron", "vix vs voxx", "vix voxx","vix vs vstoxx", "vix vstoxx",  "vix", "vx", "VOXX", "vol", 
    "FVS", "fvs", "vstoxx", "eurodollar", "ed"
]

COMMODITY_MAPPING = {
    "SR3_ED_GEN": "SR3", "SR3_ED": "SR3_ED", "sr3": "SR3", "sr1": "SR1", "so3": "S03",  "SO3_GEN":"S03",
    "er": "ER", "er3": "ER","ER_GEN": "ER", "corra": "CoRRa", "szi0": "SZI0", 
    "meeting": "meets", "meet": "meets", "sonia": "SO3", "sofr": "SR3", 
    "euribor": "ER", "meetings": "meets", "sa3": "SA3", "saron": "SA3", 
    "eurodollar": "ED", "ed": "ED", "vix": "VIX", "vx": "VIX", 
    "VOXX": "FVS", "FVS": "FVS", "fvs": "FVS", "vstoxx": "FVS", 
    "vol": "VIX", "vix vs voxx": "VIX-VOXX","vix voxx": "VIX-VOXX", "vix vs vstoxx": "VIX-VOXX", "vix vstoxx": "VIX-VOXX"
}


def extract_comdty(filepath: str) -> str:
    """Extract commodity identifier from filepath using fuzzy string matching."""
    if not filepath:
        return "Unknown"
    
    text_lower = filepath.lower().strip()
      # ✅ Step 1: Exact match check
    if text_lower in COMMODITY_MAPPING:
        return COMMODITY_MAPPING[text_lower]

    # Calculate similarity scores
    scored_matches = []
    for pattern in COMMODITY_MATCH_POOL:
        score = difflib.SequenceMatcher(None, text_lower, pattern).ratio()
        
        # Boost if substring match
        if pattern in text_lower:
            score += 0.2
        
        scored_matches.append((score, pattern))
    
    # Get best match
    scored_matches.sort(reverse=True, key=lambda x: x[0])
    best_score, best_pattern = scored_matches[0]
    
    # Return mapped commodity if score good enough
    if best_score >= 0.4:
        return COMMODITY_MAPPING.get(best_pattern, best_pattern)
    
    # Fallback to filename without extension
    return Path(filepath).stem


def get_excel_files(SUPPORTED_EXCEL_EXTENSIONS, directory_path: str = '.') -> list[str]:
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



# Function to pick port
def get_free_port(preferred_port, fallback_port):
    """Try preferred_port, if busy then use fallback_port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", preferred_port)) != 0:
            return preferred_port  # free
        else:
            return fallback_port   # fallback
