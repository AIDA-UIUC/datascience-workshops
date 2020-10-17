import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import flask

import json
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objs as go
from urllib.request import urlopen
from datetime import datetime


# ---------------------- Data and variables ---------------------------
today_date = datetime.today()
last_updated = today_date.strftime("%m-%d-%Y")

df = pd.read_csv("https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv")
# We need FIPS codes to be a string, not a float (error on their encoding)
# See https://transition.fcc.gov/oet/info/maps/census/fips/fips.txt
df["FIPS"] = df["FIPS"].apply(lambda x: f"{x:05.0f}")

last_column = df.columns[-1]

with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
    counties = json.load(response)

hovertext=df["Admin2"] + ", " + df["Province_State"]
map_fig = go.Figure(go.Choroplethmapbox(geojson=counties, locations=df["FIPS"], z=df[last_column],
                                        colorscale="Viridis",
                                        marker_opacity=0.5, marker_line_width=0,
                                        hovertext=hovertext))
map_fig.update_layout(mapbox_style="carto-positron",
                      mapbox_zoom=3, mapbox_center = {"lat": 37.0902, "lon": -95.7129},
                      margin=dict(l=20, r=20, t=20, b=20))


total_cases = df.loc[:,"1/22/20":last_column].sum()
line_fig = go.Figure(go.Scatter(x = total_cases.index, y = total_cases.values))
line_fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))

line_fig_day = go.Figure(go.Scatter(x = total_cases.index, y = total_cases.values[1:] - total_cases.values[:-1]))
line_fig_day.update_layout(margin=dict(l=20, r=20, t=20, b=20))

date_cases_by_state = df.groupby("Province_State").sum().loc[:,"1/22/20":last_column].T
date_cases_by_county = df.groupby("Admin2").sum().loc[:,"1/22/20":last_column].T

# ---------------------- Helper functions -----------------------------
def get_county_selections(state=None):
    if state is not None and state != "":
        return [
            {"label": county, "value": county}
            for county in df[df["Province_State"] == state].loc[:,"Admin2"].unique()
        ]
    return [
        {"label": county, "value": county}
            for county in df["Admin2"].unique()
    ]

def get_state_selections():
    return [
        {"label": state, "value": state}
        for state in df["Province_State"].unique()
    ]

def get_state_from_county(county):
    if county is None:
        return None
    return df[df["Admin2"] == county].loc[:, "Province_State"].unique()

def get_top_counties_cards(n=50):
    sorted_by_last_day = df.sort_values(last_column, ascending = False).head(n)
    return [
        dbc.Card([
            dbc.CardBody([
                html.H6(f"{row['Admin2']}, {row['Province_State']}"),
                html.P(f"{row[last_column]:,} total cases"),
            ])
        ])
        for index, row in sorted_by_last_day.iterrows()
    ]


# ----------------------- Dash app ------------------------------------
server = flask.Flask(__name__, template_folder = "templates")

@server.route('/')
def index():
    return flask.render_template('index.html')


#returning hello world without templates
@server.route('/hello')
def helloWorld():
    return "Hello, World!"  # return a string


@server.route('/about/')
def about():
    return flask.render_template('about.html')


app = dash.Dash(
    __name__,
    server=server,
    routes_pathname_prefix='/dash/',
    external_stylesheets=[dbc.themes.BOOTSTRAP]
)

app.layout = dbc.Container(
    [
        dbc.Row([
            dbc.Col([html.H4("COVID-19 United States Cases by County")], width = "auto"),
            dbc.Col([html.H6("Johns Hopkins University")], width = "auto"),
            dbc.Col([html.B("States/Territories")], width = "auto"),
            dbc.Col([dcc.Dropdown(id="state-selector",
                        placeholder="Select State",
                        options=get_state_selections())
            ], width = "auto"),
            dbc.Col([html.B("County")], width = "auto"),
            dbc.Col([dcc.Dropdown(id="county-selector",
                        placeholder="Select County",
                        options=get_county_selections())
            ], width = "auto"),
        ]),
        dbc.Row([
            # LEFT COLUMN
            dbc.Col([
                html.Div(get_top_counties_cards(),
                    style={"overflowY": "scroll"}),
                dbc.Card(
                    f"Last updated: {last_updated}",
                    body=True
                ),
            ], width=3, style={"height": "95vh"},),

            # CENTER COLUMN
            dbc.Col([
                dbc.Card([
                    dcc.Graph(id="map_fig", figure=map_fig)
                ], style={"max-height": "80%"}),
                dbc.Card(
                    "This is where the data came from.",
                    body=True
                )
            ], width=6, style={"height": "95vh"},),

            # RIGHT COLUMN
            dbc.Col([
                dbc.Card([
                    dcc.Graph(id="line_fig_day", figure=line_fig_day)
                ], style={"max-height": "50%"}),
                dbc.Card([
                    dcc.Graph(id="line_fig", figure=line_fig)
                ], style={"max-height": "50%"})
            ], width=3, style={"height": "95vh"},),

        ], className="h-75"),  # set height of row
    ],
    style={"height": "100vh"},
)


# ------------------------------ Callback functions --------------------------------
@app.callback(
    Output(component_id="county-selector", component_property="options"),
    [Input(component_id="state-selector", component_property="value")]
)
def update_county_selector(state):
    if state is not None and type(state) == list:
        state = state[0]
    print(f"update_county_selector({state})")
    return get_county_selections(state)


@app.callback(
    Output(component_id="state-selector", component_property="value"),
    [Input(component_id="county-selector", component_property="value")]
)
def update_state_selector(county):
    print(f"update_state_selector({county})")
    return get_state_from_county(county)


@app.callback(
    Output(component_id="map_fig", component_property="figure"),
    [Input(component_id="county-selector", component_property="value"),
     Input(component_id="state-selector", component_property="value")]
)
def update_map_fig(county, state):
    map_fig = go.Figure(go.Choroplethmapbox(geojson=counties, locations=df["FIPS"], z=df["10/2/20"],
                                            colorscale="Viridis",
                                            marker_opacity=0.5, marker_line_width=0,
                                            hovertext=hovertext))
    map_fig.update_layout(mapbox_style="carto-positron",
                          mapbox_zoom=3, mapbox_center = {"lat": 37.0902, "lon": -95.7129},
                          margin=dict(l=20, r=20, t=20, b=20))
    return map_fig


@app.callback(
    [Output(component_id="line_fig", component_property="figure"),
     Output(component_id="line_fig_day", component_property="figure")],
    [Input(component_id="county-selector", component_property="value"),
     Input(component_id="state-selector", component_property="value")]
)
def update_line_fig(county, state):
    if county is None and state is None:
        total_cases = df.loc[:,"1/22/20":last_column].sum()
        line_fig = go.Figure(go.Scatter(x = total_cases.index, y = total_cases.values))
        line_fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))
        line_fig_day = go.Figure(go.Scatter(x = total_cases.index, y = total_cases.values[1:] - total_cases.values[:-1]))
        line_fig_day.update_layout(margin=dict(l=20, r=20, t=20, b=20))
        return line_fig, line_fig_day

    if county is None:
        data = date_cases_by_state[state]
    else:
        data = date_cases_by_county[county]

    line_fig = go.Figure()
    line_fig.add_trace(go.Scatter(x = data.index, y = data.values))
    line_fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))

    line_fig_day = go.Figure()
    line_fig_day.add_trace(go.Scatter(x = data.index, y = data.values[1:] - data.values[:-1]))
    line_fig_day.update_layout(margin=dict(l=20, r=20, t=20, b=20))
    return line_fig, line_fig_day


if __name__ == '__main__':
    app.run_server(debug=True)