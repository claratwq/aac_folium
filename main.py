from datetime import datetime, timedelta
import requests
import dash
from dash import dcc, html, Input, Output, State
import dash_leaflet as dl
from geopy.geocoders import Nominatim

app = dash.Dash(__name__)
server = app.server

# --- Helper functions ---
def get_taxi_data(date_time=None):
    """Fetch taxi availability data from Data.gov.sg API"""
    url = "https://api.data.gov.sg/v1/transport/taxi-availability"
    params = {}
    if date_time:
        params["date_time"] = date_time
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        features = data.get("features", [])
        if features:
            coords = features[0]["geometry"]["coordinates"]
            return coords
    return []

def get_recent_day(selected_day):
    """Return datetime for the most recent occurrence of selected weekday"""
    days = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
    today = datetime.now()
    if not selected_day:
        return today
    target_idx = days.index(selected_day.lower())
    diff = (today.weekday() + 1 - target_idx) % 7
    return today - timedelta(days=diff)

# --- App layout ---
app.layout = html.Div([
    html.H2("🚕 Singapore Taxi Availability Map"),
    html.Div([
        html.Label("Select Day:"),
        dcc.Dropdown(
            id="day-dropdown",
            options=[
                {"label": "Today", "value": ""},
                {"label": "Monday", "value": "monday"},
                {"label": "Tuesday", "value": "tuesday"},
                {"label": "Wednesday", "value": "wednesday"},
                {"label": "Thursday", "value": "thursday"},
                {"label": "Friday", "value": "friday"},
                {"label": "Saturday", "value": "saturday"},
                {"label": "Sunday", "value": "sunday"},
            ],
            value="",
            clearable=False,
            style={"width": "200px"}
        ),
        html.Label("Select Time:"),
        dcc.Input(
            id="time-input",
            type="text",
            placeholder="HH:MM (optional)",
            style={"width": "150px"}
        ),
        html.Label("Search Location or Postal Code:"),
        dcc.Input(
            id="location-input",
            type="text",
            placeholder="e.g. 119077 or Orchard",
            style={"width": "200px"}
        ),
        html.Button("Submit", id="submit-btn", n_clicks=0)
    ], style={"display": "flex", "gap": "10px", "align-items": "center"}),

    dl.Map(
        id="taxi-map",
        center=[1.3521, 103.8198],
        zoom=12,
        style={"height": "90vh", "width": "100%"},
        children=[
            dl.TileLayer(),
            dl.LayerGroup(id="taxi-layer")
        ]
    )
])

# --- Callback ---
@app.callback(
    Output("taxi-layer", "children"),
    Output("taxi-map", "center"),
    Output("taxi-map", "zoom"),
    Input("submit-btn", "n_clicks"),
    State("day-dropdown", "value"),
    State("time-input", "value"),
    State("location-input", "value"),
    State("taxi-map", "center"),
    State("taxi-map", "zoom"),
)
def update_map(n_clicks, day, time_value, location, current_center, current_zoom):
    # --- Compute datetime ---
    date = get_recent_day(day)
    if time_value:
        try:
            hour, minute = map(int, time_value.split(":"))
            date = date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except ValueError:
            pass  # Ignore invalid time input
    date_str = date.strftime("%Y-%m-%dT%H:%M:%S")

    # --- Fetch taxi data ---
    coords = get_taxi_data(date_time=date_str)

    # --- Create blue circle markers ---
    markers = [
        dl.CircleMarker(
            center=[lat, lon],
            radius=4,
            color="blue",
            fill=True,
            fillColor="blue",
            fillOpacity=0.7,
            stroke=False
        )
        for lon, lat in coords
    ]
    marker_layer = dl.LayerGroup(markers)

    # --- Zoom to searched location if provided ---
    new_center = current_center
    new_zoom = current_zoom
    if location:
        geolocator = Nominatim(user_agent="sg_taxi_app")
        try:
            loc = geolocator.geocode(f"{location}, Singapore")
            if loc:
                new_center = [loc.latitude, loc.longitude]
                new_zoom = 15
        except:
            pass

    return marker_layer, new_center, new_zoom

# --- Run server ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860, debug=True)
