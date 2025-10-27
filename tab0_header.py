from dash import dcc, html
import dash_bootstrap_components as dbc
import socket
from difflib import SequenceMatcher
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
                className='form-control',
                maxHeight=310,
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
                className='form-control',
                maxHeight=310,
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
        #drop down for lookback period with custom input box
        dbc.Col([
            html.Label("Lookback Period", style={"color": "#c0c4cc","fontWeight": "500","fontSize": "14px","marginBottom": "4px"}),
            # --- Side-by-side layout ---
            dbc.Row([
                dbc.Col(
                    dcc.Dropdown(
                        id='lookback_dropdown',
                        options=lookback_options,
                        value=DEFAULT_LOOKBACK,
                        clearable=False,
                        placeholder="Select...",
                        searchable=True,
                        className='form-control'
                    ),
                    width=7,
                    style={"paddingRight": "1px"}
                ),
                dbc.Col(
                    dcc.Input(
                        id='lookback_custom',
                        type='text',
                        placeholder="Custom...",
                        debounce=True,
                        style={
                            'width': '100%',
                            'height': '38px',
                            'borderRadius': '6px',
                            'border': '1px solid #ccc',
                            'paddingLeft': '1px'
                        }
                    ),
                    width=5,
                    style={"paddingLeft": "5px"}
                )
            ]),
        ]),

        dbc.Col([
            html.Label(" "),
            dbc.Button("Load", id='load-btn', color='primary', className='mt-4', n_clicks=0)
        ])
    ], className='mb-4')
    
    return header_component



# Commodity matching configuration
COMMODITY_GROUPS = {
    "SR3": {"SR3_ED_GEN", "SR3_ED", "sr3", "sofr", "SR3", "eurodollar", "ed"},
    "SR1": {"sr1", "SR1_GEN"},
    "SO3": {"so3", "SO3_GEN", "sonia"},
    "ER": {"euribor", "er", "ER_GEN", "Euro"},
    "ER3": {"er3", "ESTR", "ESTR_GEN", "ER3_GEN"},
    "CRA": {"corra", "corra_gen", "cra"},
    "SA3": {"sa3", "saron", "SA3_GEN"},
    "SZI0": {"szi0", "SZIO_GEN"},
    "MEETS": {"meeting", "meet", "meetings", "meets", "MEETS_GEN", "fomc"},
    "VIX": {"vix", "vx", "vol"},
    "FVS": {"VOXX", "FVS", "fvs", "vstoxx", "vstox", "vox"},
    "VIX-VOX": {
        "vix vs voxx", "vix voxx", "vix vs vstoxx", "vix vstoxx", "vix vs voxx", "vix voxx", "vix vs vstoxx", "vix vstoxx", "vix-voxx", "vix-voxx",
        "vx vs vox", "vx vox", "vx vs vstox", "vx vstox", "vx vs vox", "vx vox", "vx vs vstox", "vx vstox", "vx-vox", "vx-vox",
        "vix vs fvs", "vix fvs", "vix vs fvs", "vix fvs", "vix vs fvs", "vix fvs", "vix vs fvs", "vix fvs", "vix-fvs", "vix-fvs",
        "vx vs fvs", "vx fvs", "vx vs fvs", "vx fvs", "vx vs fvs", "vx fvs", "vx vs fvs", "vx fvs", "vx-fvs", "vx-fvs",
    },
}


COMMODITY_MAPPING = {alias.lower(): key for key, aliases in COMMODITY_GROUPS.items() for alias in aliases}
# Create match pool for fuzzy search
COMMODITY_MATCH_POOL = list(COMMODITY_MAPPING.keys())

# ======================
# Extract commodity function
# ======================
def extract_comdty(filepath: str) -> str:
    """Extract commodity identifier from filepath using fuzzy string matching."""
    if not filepath:
        return "Unknown"
    
    text_lower = filepath.lower().strip()
    
    # Exact match first
    if text_lower in COMMODITY_MAPPING:
        return COMMODITY_MAPPING[text_lower]

    # Fuzzy match
    scored_matches = []
    for pattern in COMMODITY_MATCH_POOL:
        score = SequenceMatcher(None, text_lower, pattern).ratio()
        if pattern in text_lower:
            score += 0.2
        scored_matches.append((score, pattern))
    
    scored_matches.sort(reverse=True, key=lambda x: x[0])
    best_score, best_pattern = scored_matches[0]
    
    if best_score >= 0.4:
        return COMMODITY_MAPPING.get(best_pattern, best_pattern)
    
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
