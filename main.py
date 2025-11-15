import dash
from dash import Dash, html, dcc, Input, Output, State
import dash_leaflet as dl
import pandas as pd
import requests

from helper import haversine,get_coordinates_from_postal, get_route, decode_polyline

headers = {"Authorization": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo1ODM4LCJmb3JldmVyIjpmYWxzZSwiaXNzIjoiT25lTWFwIiwiaWF0IjoxNzYzMTMzMzg5LCJuYmYiOjE3NjMxMzMzODksImV4cCI6MTc2MzM5MjU4OSwianRpIjoiZWJkMmQyOTEtNzVlYS00Zjc1LWE0YTgtZDY4ZDU0Mzc0YjdkIn0.BK-F3sHEJ701hM-OrV5ekIS_cixetWg8WXudnxQkoeXwG9-POphJhMyL-JqeANpTf1py-zQzoa-kCljxOcSd3hWBrDxlqauzeABHTS4FHQhsLhUOVeofNn0sYYdk19tuKk4Ctq3BHUOGJylLJVPw3FY2UXzUTxaGDcVhadr9D78XA822XuuwjPPFmeiabrRuIu8L_709Wacy3LZxman0A9tJmVe46lNH-KdGbF30kKvPicntOIvhH-4PQ81ofaNYNbuaMZXJumyGqvUK-VmoNS7Qt5yZ712VgSMqSbjHOXvoW2CdrDKt07Y4x2Jhdj4Br1AYplyq7QT0zYttoa7o_Q"}


# =========================
# Load AAC Data
# =========================
aac_df = pd.read_csv("AAC_locations.csv")

all_aac_markers = [
    dl.Marker(
        position=[row["LATITUDE"], row["LONGITUDE"]],
        children=dl.Popup(row["SEARCHVAL"])
    )
    for _, row in aac_df.iterrows()
]

# =========================
# Dash App
# =========================
app = Dash(__name__)

app.layout = html.Div([
    html.H3("Find Nearest Active Ageing Centres"),
    html.Div([
        dcc.Input(id="postal-input", type="text", placeholder="Enter postal code..."),
        html.Button("Find AACs", id="submit-btn")
    ]),
    dl.Map([
        dl.TileLayer(),
        dl.LayerGroup(id="aac-layer"),
        dl.LayerGroup(id="route-layer"),
        dl.LayerGroup(id="user-marker")
    ], 
        id="map", 
        style={'width': '100%', 'height': '600px'},
        zoom=12, 
        center=[1.3521, 103.8198],
        #bounds = [[1.20, 103.60], [1.48, 104.05]],
        #boundsOptions={"padding": [0, 0]} 
    ),
    html.Div(id="output-info")
])
# =========================
# Call back
# =========================
@app.callback(
    Output("map", "zoom"),
    Input("submit-btn", "n_clicks"),
    State("postal-input", "value"),
    prevent_initial_call=True
)
def update_zoom(n_clicks, postal):
    default_zoom = 12
    target_zoom = 15.0001  # tiny bump ensures Leaflet treats zoom as a new view
    if not n_clicks or not postal or postal.strip() == "":
        return default_zoom
    return target_zoom

@app.callback(
    [Output("aac-layer", "children"),
     Output("route-layer", "children"),
     Output("user-marker", "children"),
     Output("output-info", "children"),
     Output("map", "center")],
     Input("submit-btn", "n_clicks"),
     State("postal-input", "value")
)
def find_nearest_aac(n_clicks, postal):
    # Default SG bounds
    #default_bounds = [[1.20, 103.60], [1.48, 104.05]]
    default_center = [1.3521, 103.8198]
    # =========================
    # 1️⃣ No click or empty postal → show all AACs
    # =========================
    if not n_clicks or not postal or postal.strip() == "":
        return all_aac_markers, [], [], "", default_center

    # =========================
    # 2️⃣ Geocode postal code
    # =========================
    geo_url = f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={postal}&returnGeom=Y&getAddrDetails=Y&pageNum=1"
    r = requests.get(geo_url, headers=headers).json()

    if not r["results"]:
        return all_aac_markers, [], [], "Postal code not found", default_center

    user_lat = float(r["results"][0]["LATITUDE"])
    user_lon = float(r["results"][0]["LONGITUDE"])
    user_marker = [dl.Marker(position=[user_lat, user_lon], children=dl.Popup("You are here"))]
    #center = [user_lat,user_lon]
    # =========================
    # 3️⃣ Find 3 nearest AACs
    # =========================
    aac_df["dist_km"] = aac_df.apply(lambda x: haversine(user_lat, user_lon, x["LATITUDE"], x["LONGITUDE"]), axis=1)
    nearest = aac_df.nsmallest(3, "dist_km")

    colors = ["red", "blue", "green"]
    route_lines, info_cards = [], []
    all_coords = [(user_lat, user_lon)]

    for i, (_, row) in enumerate(nearest.iterrows()):
        route = get_route((user_lat, user_lon), (row["LATITUDE"], row["LONGITUDE"]))
        if route:
            all_coords += route["coords"]
            route_lines.append(dl.Polyline(positions=route["coords"], color=colors[i], weight=4))
            info_cards.append(html.Div([
                html.B(row["SEARCHVAL"]), html.Br(),
                f"Walk Distance: {route['Walk distance']/1000:.2f} km | Time: {route['time']/60:.1f} min",
                html.Br(),
                f"Directions: {route['Instructions']}"
            ], style={"margin":"5px"}))

    # Add nearest AAC markers
    aac_markers = [
        dl.Marker(position=[row["LATITUDE"], row["LONGITUDE"]],
                  children=dl.Popup(f"{row['SEARCHVAL']} ({row['dist_km']:.2f} km away)"))
        for _, row in nearest.iterrows()
    ]

    # =========================
    # 4️⃣ Auto-fit map bounds
    # =========================
    valid_coords = [(lat, lon) for lat, lon in all_coords if lat is not None and lon is not None]
    print(valid_coords)
    if len(valid_coords) < 2:
        #bounds = default_bounds
        print('no valid coordinates')
    else:
        all_coords = [(user_lat, user_lon)] + [(row["LATITUDE"], row["LONGITUDE"]) for _, row in nearest.iterrows()]
        lats = [c[0] for c in all_coords]
        lons = [c[1] for c in all_coords]
        #bounds = [[min(lats), min(lons)], [max(lats), max(lons)]]
        #print(all_coords)
        center = [(min(lats)+max(lats))/2, (min(lons)+max(lons))/2]

        lats = [c[0] for c in valid_coords]
        lons = [c[1] for c in valid_coords]
        bounds = [[min(lats), min(lons)], [max(lats), max(lons)]]
        #print('bounds ', bounds)
        print(center)
    # Combine all AACs if you want
    return aac_markers, route_lines, user_marker, info_cards, center


if __name__ == "__main__":
    #app.run(debug = False)
    app.run(host="0.0.0.0", port=7860, debug=True)
