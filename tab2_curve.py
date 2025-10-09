from dash import dcc, html
import dash_bootstrap_components as dbc
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