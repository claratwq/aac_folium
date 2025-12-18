from flask import Flask, render_template_string, request
import folium
import pandas as pd
from helper import get_token, haversine, get_coordinates_from_postal, get_route

headers = get_token()
print(headers)

aac_df = pd.read_csv("active_ageing_centres_incremental_w_latlon.csv")

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Active Ageing Centres Finder</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <style>
        html, body {
            height: 100%;
            width: 100%;
            margin: 0;
            padding: 0;
            overflow: hidden;
        }

        #map-container {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            height: 100vh;
            width: 100vw;
        }

        /* Force Folium / Leaflet iframe to fill container */
        iframe {
            position: absolute;
            top: 0;
            left: 0;
            height: 100vh !important;
            width: 100vw !important;
            border: none;
        }

        .form-box {
            position: fixed;
            top: 12px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 9999;
            background: white;
            padding: 8px 12px;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }
    </style>

</head>

<body>
    <div class="form-box">
        <form method="POST">
            <input
                type="text"
                name="postal"
                placeholder="Enter postal code"
                value="{{ postal or '' }}"
                style="padding:6px;"
            >
            <button type="submit">Find AACs</button>
        </form>
    </div>

    <div id="map-container">
        {{ map_html|safe }}
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    postal = request.form.get("postal")

    sg_center = [1.3521, 103.8198]
    folium_map = folium.Map(
        location=sg_center,
        zoom_start=12,
        scrollWheelZoom=True,
        dragging=True,
        zoomControl=True
    )

    # Mobile-friendly scrolling behaviour
    folium_map.get_root().html.add_child(folium.Element("""
    <script>
    document.addEventListener("DOMContentLoaded", function() {
        const map = document.querySelector(".leaflet-container");
        map.addEventListener('touchmove', function(e) {
            e.stopPropagation();
        }, { passive: true });
    });
    </script>
    """))

    all_coords = []

    if not postal:
        # Show all AACs only
        for _, row in aac_df.iterrows():
            folium.Marker(
                location=[row["latitude"], row["longitude"]],
                popup=row["Centre Name"]
            ).add_to(folium_map)
            all_coords.append([row["latitude"], row["longitude"]])

    else:
        try:
            # User location
            user_lat, user_lon, addr = get_coordinates_from_postal(postal)

            folium.Marker(
                location=[user_lat, user_lon],
                popup="You are here",
                icon=folium.Icon(
                    color="orange",
                    icon="home",
                    prefix="fa"
                )
            ).add_to(folium_map)

            all_coords.append([user_lat, user_lon])

            # Compute distances
            aac_df["dist_km"] = aac_df.apply(
                lambda x: haversine(
                    user_lat, user_lon,
                    x["latitude"], x["longitude"]
                ),
                axis=1
            )

            nearest = aac_df.nsmallest(3, "dist_km")
            colors = ["red", "blue", "green"]

            for i, (_, row) in enumerate(nearest.iterrows()):
                route = get_route(
                    (user_lat, user_lon),
                    (row["latitude"], row["longitude"])
                )

                # Draw route immediately
                if route and route.get("coords"):
                    folium.PolyLine(
                        route["coords"],
                        color=colors[i],
                        weight=4,
                        opacity=0.85
                    ).add_to(folium_map)

                    all_coords.extend(route["coords"])

                # Popup content (shown only on click)
                popup_html = f"""
                <b>{row['Centre Name']}</b><br>
                <b>Address:</b> {row['Address']}<br>
                <b>Operating Hours:</b> {row['Operating Hours']}<br>
                <b>Walk Distance:</b> {route['Walk distance']/1000:.2f} km<br>
                <b>Time:</b> {route['time']/60:.1f} min<br><br>
                <b>Directions:</b><br>
                """

                for step in route["Instructions"]:
                    popup_html += f"- {step}<br>"

                folium.Marker(
                    location=[row["latitude"], row["longitude"]],
                    popup=folium.Popup(popup_html, max_width=320),
                    icon=folium.Icon(color=colors[i])
                ).add_to(folium_map)

                all_coords.append([row["latitude"], row["longitude"]])

            # Fit map bounds
            if all_coords:
                folium_map.fit_bounds(all_coords)

        except Exception as e:
            folium.Marker(
                location=sg_center,
                popup=f"Error: {str(e)}",
                icon=folium.Icon(color="red")
            ).add_to(folium_map)

    map_html = folium_map._repr_html_()
    return render_template_string(
                HTML_TEMPLATE,
                map_html=map_html,
                postal=postal
            )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
