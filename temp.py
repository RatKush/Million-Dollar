import dash
from dash import html
import dash_ag_grid as dag

# Simple test data
data = [
    {
        "Contract": "H25", 
        "roll_down": 0.15, 
        "roll_up": 0.22,
        "roll_display": "▲0.15 | 0.22▲"  # Create this in Python
    },
    {
        "Contract": "M25", 
        "roll_down": -0.25, 
        "roll_up": -0.18,
        "roll_display": "▼-0.25 | -0.18▼"  # Create this in Python
    }
]
columnDefs = [
    {
    "field": "roll_display",
    "headerName": "Roll Combined",
    "width": 180
}

]

app = dash.Dash(__name__)
app.layout = html.Div([
    dag.AgGrid(
        id="test-grid",
        columnDefs=columnDefs,
        rowData=data,
        style={"height": "300px"}
    )
])

if __name__ == "__main__":


    app.run(debug=True, port=8051)
