from flask import Flask, render_template_string, request
import folium
import pandas as pd
from helper import get_token, haversine, get_coordinates_from_postal, get_route

headers = get_token()
aac_df = pd.read_csv("AAC_locations.csv")

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Active Ageing Centres Finder</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {{ folium_css|safe }}
    {{ folium_js|safe }}
</head>
<body>
    <h3 style="text-align:center;">Find Nearest Active Ageing Centres</h3>
    <form method="POST" style="text-align:center; margin:10px;">
        <input type="text" name="postal" placeholder="Enter postal code" style="padding:8px; width:200px;">
        <button type="submit" style="padding:8px;">Find AACs</button>
    </form>
    <div style="width: 100%; max-width: 800px; margin:auto;">
        {{ map_html|safe }}
    </div>
    <div style="width: 100%; max-width: 800px; margin:auto; padding:10px;">
        {% if info %}
            {{ info|safe }}
        {% endif %}
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    postal = request.form.get("postal")
    sg_center = [1.3521, 103.8198]
    folium_map = folium.Map(location=sg_center, zoom_start=None)
    info_html = ""
    all_coords = []

    if not postal:
        # Show all AACs
        for _, row in aac_df.iterrows():
            folium.Marker(
                location=[row["LATITUDE"], row["LONGITUDE"]],
                popup=row["SEARCHVAL"]
            ).add_to(folium_map)
            all_coords.append([row["LATITUDE"], row["LONGITUDE"]])
    else:
        try:
            # User location
            user_lat, user_lon, addr = get_coordinates_from_postal(postal)
            folium.Marker(
                location=[user_lat, user_lon],
                popup="You are here",
                icon=folium.Icon(color="orange")
            ).add_to(folium_map)
            all_coords.append([user_lat, user_lon])

            # Find nearest 3 AACs
            aac_df["dist_km"] = aac_df.apply(
                lambda x: haversine(user_lat, user_lon, x["LATITUDE"], x["LONGITUDE"]),
                axis=1
            )
            nearest = aac_df.nsmallest(3, "dist_km")
            colors = ["red", "blue", "green"]

            for i, (_, row) in enumerate(nearest.iterrows()):
                route = get_route((user_lat, user_lon), (row["LATITUDE"], row["LONGITUDE"]))
                if route and route["coords"]:
                    folium.PolyLine(route["coords"], color=colors[i], weight=4).add_to(folium_map)
                    all_coords.extend(route["coords"])
                    info_html += f"<b>{row['SEARCHVAL']}</b><br>Walk Distance: {route['Walk distance']/1000:.2f} km | Time: {route['time']/60:.1f} min<br>Directions:<br>"
                    for step in route["Instructions"]:
                        info_html += f"- {step}<br>"

                folium.Marker(
                    location=[row["LATITUDE"], row["LONGITUDE"]],
                    popup=f"{row['SEARCHVAL']} ({row['dist_km']:.2f} km away)",
                    icon=folium.Icon(color=colors[i])
                ).add_to(folium_map)
                all_coords.append([row["LATITUDE"], row["LONGITUDE"]])

            # Auto-fit map to all coordinates
            if all_coords:
                folium_map.fit_bounds(all_coords)

        except Exception as e:
            info_html = f"Error: {str(e)}"

    map_html = folium_map._repr_html_()
    folium_css = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css"/>'
    folium_js = '<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>'

    return render_template_string(HTML_TEMPLATE, map_html=map_html, folium_css=folium_css, folium_js=folium_js, info=info_html)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
