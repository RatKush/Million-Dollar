from dash import html, dcc
# mailer.py
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import os

sample_notes = ["Short EDZ5 vs EDM6", "Long SFRH5 vs SFRM5"]

footer_component = html.Footer([
    html.Div([
        # Left: Feedback form
        html.Div([
            html.H4("Send Feedback / Suggestions", style={
                "color": "#c0c4cc", "fontSize": "16px", "fontWeight": "400", "marginBottom": "12px"
            }),
            dcc.Dropdown(
                id="feedback-type",
                className="custom-dropdown",
                clearable=False,
                options=[
                    {"label": "General Feedback", "value": "General"},
                    {"label": "Bug Report", "value": "Bug"},
                    {"label": "Feature Request", "value": "Feature"},
                    {"label": "Data Issue", "value": "Data"}
                ],
                value="General",
                style={
                    "width": "100%", "backgroundColor": "#2b2e35", "color": "#00bcd4",
                    "border": "1px solid #3a3f4b", "borderRadius": "8px", "padding": "2px",
                }
            ),
            dcc.Textarea(
                id="feedback-text",
                placeholder="Write your feedback here...",
                style={
                    "width": "100%", "height": "100px", "backgroundColor": "#2b2e35",
                    "color": "#c0c4cc", "border": "1px solid #3a3f4b", "borderRadius": "8px",
                    "padding": "10px"
                }
            ),
            html.Button(
                id="submit-feedback",children="Submit",className="tab7-button",n_clicks=0, style={"marginTop": "10px", "width": "120px"}
            ),
            dcc.Interval(id="reset-button-label", interval=2000, n_intervals=0, disabled=True)
        ], style={"width": "48%"}),

        # Right: Trades to Look Out For
        html.Div([
            html.H4("Trades to Look Out For", style={
                "color": "#c0c4cc", "fontSize": "16px", "fontWeight": "400", "marginBottom": "12px"
            }),
            dcc.Input(
                id="trade-note-input",
                placeholder="e.g., Short EDZ5 vs EDM6",
                style={
                    "width": "100%", "backgroundColor": "#2b2e35", "color": "#c0c4cc",
                    "border": "1px solid #3a3f4b", "borderRadius": "8px", "padding": "8px"
                }
            ),
            html.Button("Add", id="add-trade-note", className="tab7-button", style={
                "marginTop": "10px", "width": "100px"
            }),
            html.Div(
            id="trade-note-list",
            children=[],  # will be filled dynamically by callback
            style={
                "marginTop": "20px","border": "1px solid #3a3f4b", "borderRadius": "8px","backgroundColor": "#1f2128",
                "color": "#c0c4cc","padding": "10px","maxHeight": "200px","overflowY": "auto","fontSize": "14px"
            }
        ),
            dcc.Store(id="trade-notes-store", storage_type="local")
        ], style={"width": "48%"}),
    ], style={
        "display": "flex",
        "justifyContent": "space-between",
        "gap": "4%",
        "flexWrap": "wrap"
    }),



    html.Hr(style={"borderTop": "1px solid #3a3f4b", "margin": "40px 0"}),

############################################   # Links Section################################################
    html.Div([
        html.Div([
            html.H5("🌐 Source", style={
                "color": "#c0c4cc", "marginRight": "16px", "marginBottom": "0"
            }),
            html.A("Mail", href="mailto:ratkush2023@gmail.com?subject=Suggestion", target="_blank",
                   style={"color": "#c0c4cc", "marginRight": "10px"}),
            html.Span("|", style={"color": "#888888", "marginRight": "10px"}),
            html.A("GitHub", href="https://github.com/RatKush/Million-Dollar", target="_blank",
                   style={"color": "#c0c4cc", "marginRight": "10px"}),
            html.Span("|", style={"color": "#888888", "marginRight": "10px"}),
            html.A("Hosted version", href="https://million-dollar.onrender.com/", target="_blank",
                   style={"color": "#c0c4cc"})
        ], style={
            "display": "flex", "flexWrap": "wrap", "alignItems": "center", "padding": "10px 0"
        }),

        html.Div([
            html.H5("📊 Trading refs", style={
                "color": "#c0c4cc", "marginRight": "16px", "marginBottom": "0"
            }),
            html.A("Economic Calendar", href="https://www.investing.com/economic-calendar/", target="_blank",
                   style={"color": "#c0c4cc", "marginRight": "12px"}),
            html.Span("|", style={"color": "#888888", "marginRight": "12px"}),
            html.A("Central bank rates", href="https://www.investing.com/central-banks/", target="_blank",
                   style={"color": "#c0c4cc", "marginRight": "12px"}),
            html.Span("|", style={"color": "#888888", "marginRight": "12px"}),
            html.A("SOFR daily fixing", href="https://www.newyorkfed.org/markets/reference-rates/sofr", target="_blank",
                   style={"color": "#c0c4cc", "marginRight": "12px"}),
            html.Span("|", style={"color": "#888888", "marginRight": "12px"}),
            html.A("EFFR daily fixing", href="https://www.newyorkfed.org/markets/reference-rates/effr", target="_blank",
                   style={"color": "#c0c4cc", "marginRight": "12px"}),
            html.Span("|", style={"color": "#888888", "marginRight": "12px"}),
            html.A("EFFR rate cycle", href="https://fred.stlouisfed.org/series/FEDFUNDS", target="_blank",
                   style={"color": "#c0c4cc", "marginRight": "12px"}),
            html.Span("|", style={"color": "#888888", "marginRight": "12px"}),
            html.A("Fed Reserve", href="https://www.federalreserve.gov/", target="_blank",
                   style={"color": "#c0c4cc"})
        ], style={
            "display": "flex", "flexWrap": "wrap", "alignItems": "center",
            "justifyContent": "flex-start", "padding": "20px 0"
        }),
    ]),



    html.Hr(style={"borderTop": "1px solid #3a3f4b", "margin": "10px 0"}),
############################################################## bottom ##################################
   
    # Bottom Footer Bar
    html.Div("2025 Million Dollar • Version 1.0.0",
             style={"textAlign": "center", "color": "#777", "fontSize": "14px"})
], style={
    "backgroundColor": "#2b2e35", "padding": "40px 20px", "marginTop": "450px",
    "borderTop": "1px solid #3a3f4b", "borderRadius": "8px"
})






##################################################### mailer ########################################
# mailer.py
import smtplib
from email.message import EmailMessage


load_dotenv()
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


def send_feedback_email(category, msg):
    email = EmailMessage()
    email["Subject"] = f"New Feedback - {category}"
    email["From"] = EMAIL_ADDRESS
    email["To"] = EMAIL_ADDRESS
    email.set_content(f"Feedback Category: {category}\n\nMessage:\n{msg}")

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(email)