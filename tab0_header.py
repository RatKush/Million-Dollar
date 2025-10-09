from dash import dcc, html
import dash_bootstrap_components as dbc


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
    ], className='mb-4')
    
    return header_component
