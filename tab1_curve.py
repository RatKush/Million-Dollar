from dash import dcc, html
import dash_bootstrap_components as dbc
import dash_ag_grid as dag

def create_tab1_view():
    view= dcc.Tab(label='Curve View', value='tab1',
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
            ])
    return view
    