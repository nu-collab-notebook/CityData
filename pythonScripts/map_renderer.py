# This file handles rendering  the map and other map related things such as boundaries and markers. (possibly split the code later once the file is large to modularise the code)
import folium
import json
import os
import pandas as pd
from folium.plugins import MarkerCluster

import matplotlib.colors as mcolors

import geopandas as gpd

from pythonScripts import  BusNet4 as bus
from shapely.geometry import shape


def generate_base_map(config):
    """Generates a base folium map centered on the citys location."""
    return folium.Map(location=config.CENTRE, zoom_start=12, tiles="OpenStreetMap")

def add_boundaries(map_object, config):
    """
    Adds all city boundaries to an existing map, utilises the add_selected_boundary.
    Parameters:
    - map_object: The map object.
    - config: The city config file.

    Returns:
    - The updated map with all boundaries.
    """
    if config is None:
        print("Error: No city config provided.")
        return map_object

    available_boundaries = [attr for attr in dir(config) if attr.startswith("b_")] #filters by the prepend b_ which each config file boundary variables should have.

    if not available_boundaries:
        print(f"No boundaries found for {config.CITY_NAME}.")
        return map_object

    for boundary_type in available_boundaries:
        #print(f"Adding boundary: {boundary_type}")

        
        map_object = add_selected_boundary(map_object, config, boundary_type)

    return map_object


def add_selected_boundary(map_object, config, boundary_type):
    """
    Adds only the selected boundary to the map.

    Parameters:
    - map_object: The map object.
    - config: The city config file.
    - boundary_type: The specific boundary to display.
    
    Returns:
    - Updated map with the selected boundary.
    """
    if config is None:
        print("Error: No city config provided.")
        return map_object

    boundary_path = getattr(config, boundary_type, None)

    if not boundary_path or not os.path.exists(boundary_path):
        print(f"Boundary file not found at {boundary_path}")
        return map_object

    try:
        with open(boundary_path, "r") as f:
            boundary_data = json.load(f)
        # Boundary styles
        folium.GeoJson(
            boundary_data,
            name=f'{config.CITY_NAME} {boundary_type.replace("b_", "").replace("_", " ").title()}',
            style_function=lambda feature: {
                "color": "blue",
                "weight": 2,           
                "fillColor": "#00ffff",
                "fillOpacity": 0.2,
            },
            highlight_function=lambda feature: {
                "color": "darkblue",
                "weight": 3,
                "fillColor": "#008b8b",
                "fillOpacity": 0.4,
            }
        ).add_to(map_object)
        #Get the names of boundaries from the properties in the geojson.
        extracted_features = []
        for feature in boundary_data["features"]:
            properties = feature.get("properties", {})
            geometry = feature.get("geometry", {})
            extracted_features.append({
                "geometry": shape(geometry),
                "properties": properties
            })

        # Convert features into a GeoDataFrame.
        gdf = gpd.GeoDataFrame(extracted_features)

        for _, row in gdf.iterrows():
            properties = row.get("properties", {})

            # Multiple possible keys for the boundary name empty string if none found.
            boundary_name = (
                properties.get("AreaName") or
                properties.get("PolicyRef") or
                properties.get("RefNo") or
                ""
            )
            # Styling for boundary name for clear visibility
            centroid = row.geometry.centroid
            folium.Marker(location=[centroid.y, centroid.x],
                icon=folium.DivIcon(html=f"""
                    <div style="
                        font-size: 14px;
                        font-weight: bold;
                        color: white;
                        text-shadow: -1px -1px 0 black, 1px -1px 0 black, -1px 1px 0 black, 1px 1px 0 black;
                        text-align: center;
                        padding: 3px;
                        border-radius: 5px;
                    ">
                        {boundary_name}
                    </div>
                """)).add_to(map_object)

    except Exception as e:
        print(f"Error: Unable to load boundary data. Details: {e}")

    return map_object

def add_postcode_markers(map_object, df):
    """Adds postcode markers to an existing map."""
    if df is None or df.empty:
        print("No valid postcodes to display.")
        return map_object

    marker_cluster = MarkerCluster().add_to(map_object)

    for _, row in df.iterrows():
        folium.Marker(
            location=(row["Latitude"], row["Longitude"]),
            popup=f"<b>{row['Postcode']}</b>",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(marker_cluster)

    return map_object

def combine_map_layers(config, *layer_functions):
    """Generates a base map and applies multiple dynamic layers, functions that return map ui elements can be passed in"""
    map_object = generate_base_map(config)

    for layer_function in layer_functions:
        if callable(layer_function):
            map_object = layer_function(map_object)

    return map_object



def get_exact_color(value, min_val, max_val, is_population):
    """
    Gets the exact color for both heatmap & markers.
    - value: The value to be color-mapped.
    - min_val: The minimum value in the dataset.
    - max_val: The maximum value in the dataset.
    - is_population: If True, uses the population range. If False, uses affluence.
    TODO: make this even more dynamic for more data interests

    Returns:
    - A hex color string.
    """
    colormap = mcolors.LinearSegmentedColormap.from_list(
        "deprivation_gradient",
        ["darkred", "#D73027", "#FC8D59", "yellow", "#91CF60", "#1A9850", "lightblue"]
    )
    

    if pd.isna(value) or value == 0:
        return "black"  # Black for missing or zero vals
   
    norm_score = (value - min_val) / (max_val - min_val)

    return mcolors.rgb2hex(colormap(norm_score))  # Convert to hex color




def add_dynamic_heatmap(map_object, df, column_name, label):
    """
    Adds a dynamic heatmap based on a selected column.
    - `map_object`: The map object.
    - `df`: The DataFrame containing postcode data.
    - `column_name`: The column used for heatmap values.
    - `label`: The label used for the legend.
    """
    if df is None or df.empty:
        print("Error: No valid postcode data.")
        return map_object

    print(f"Adding {label} heatmap...")
    
    min_value = df[column_name].min()
    max_value = df[column_name].max()

    heatmap_layer = folium.FeatureGroup(name=label)

    for _, row in df.iterrows():
        value = float(row[column_name])
        exact_color = get_exact_color(value, min_value, max_value, column_name == "Population")

        folium.CircleMarker(
            location=(row["Latitude"], row["Longitude"]),
            radius=6,
            color=exact_color,
            fill=True,
            fill_color=exact_color,
            fill_opacity=0.3,
            opacity=0.2
        ).add_to(heatmap_layer)

    map_object.add_child(heatmap_layer)

      # add legend
    map_object = add_color_legend(map_object, min_value, max_value, label)
    print(f"{label} heatmap added.")
    
    return map_object


def add_dynamic_markers(map_object, df, column_name):
    """
    Adds postcode markers colored by Affluence, Population, or Households.
    
    - `map_object`: The folium map object.
    - `df`: The DataFrame containing postcode data.
    - `column_name`: The column to use for marker colors.
    """
    if df is None or df.empty:
        print("No valid postcode data.")
        return map_object

    print(f"Adding postcode markers")

    min_value = df[column_name].min()
    max_value = df[column_name].max()

    marker_cluster = MarkerCluster(name="Postcode Markers").add_to(map_object)

    for _, row in df.iterrows():
        value = float(row[column_name])

        # Determine if population, households, or affluences for coloring
        is_population = column_name == "Population"
        is_households = column_name == "Households"
        exact_color = get_exact_color(value, min_value, max_value, is_population or is_households)

        # relevant details to display in marker popups
        popup_text = f"""
        <b>{row['Postcode']}</b><br>
        Population: {int(row['Population'])}<br>
        Households: {int(row['Households'])}<br>
        Affluence Score (IMD): {row['Index of Multiple Deprivation']:.2f}
        """

        folium.Marker(
            location=(row["Latitude"], row["Longitude"]),
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color="gray", icon="info-sign")
        ).add_to(marker_cluster)

        # Overlays a small color circle behind the marker so heatmaps still shows when zoomed in
        folium.Circle(
            location=(row["Latitude"], row["Longitude"]),
            radius=12,
            color=exact_color,
            fill=True,
            fill_color=exact_color,
            fill_opacity=0.8
        ).add_to(map_object)

    print("Postcode markers added.")
    return map_object

def add_color_legend(map_object, min_value, max_value, label="Legend"):
    """
    Adds a color legend to the map so its clearer to understand the heatmap.
    - min_value: The lowest value in the dataset.
    - max_value: The highest value in the dataset.
    - label: Title for the legend.
    """
    legend_html = f"""
     <div style="position: fixed;
                bottom: 20px; left: 20px; width: 260px; height: 100px;
                background-color: white; z-index:9999; font-size:14px;
                border:2px solid grey; padding:10px;">
        <b>{label}</b><br>
        <i style="background:darkred; width: 20px; height: 10px; display: inline-block;"></i> Lowest ({min_value})<br>
        <i style="background:yellow; width: 20px; height: 10px; display: inline-block;"></i> Midpoint<br>
        <i style="background:lightblue; width: 20px; height: 10px; display: inline-block;"></i> Highest ({max_value})
     </div>
    """
    map_object.get_root().html.add_child(folium.Element(legend_html))
    return map_object


##############################################################################################################################
#region travel:



    
def display_routes_on_map(map_object, routes):
    """
    Displays routes on the map with specific colors.
    """
    if map_object is None:
        print("⚠ Cannot draw routes: map_object is None.")
        return None

    if routes is None or not isinstance(routes, dict):
        print("⚠ Invalid routes provided.")
        return map_object

    colors = {
        "Walking": "blue",
        "Cycling": "green",
        "Driving": "red",
        "Bus": "purple"
    }

    for mode, coords in routes.items():
        if coords:
            folium.PolyLine(coords, color=colors.get(mode, "gray"), weight=5, opacity=0.8, tooltip=mode).add_to(map_object)

    return map_object


def add_route_legend(map_object):
    """
    Adds a legend to explain route colors.
    """
    legend_html = """
     <div style="position: fixed;
                bottom: 20px; left: 20px; width: 200px; height: 150px;
                background-color: white; z-index:9999; font-size:14px;
                border:2px solid grey; padding:10px;">
        <b>Route Legend</b><br>
        <i style="background:blue; width: 20px; height: 10px; display: inline-block;"></i> Walking<br>
        <i style="background:green; width: 20px; height: 10px; display: inline-block;"></i> Cycling<br>
        <i style="background:red; width: 20px; height: 10px; display: inline-block;"></i> Driving<br>
        <i style="background:orange; width: 20px; height: 10px; display: inline-block;"></i> Bus
     </div>
    """
    map_object.get_root().html.add_child(folium.Element(legend_html))



def show_closest_routes_only(config, map_object, route_df):
    """
    Displays arrows from each postcode to its closest commercial zone,
    and overlays all boundaries.
    """
    #Add boundaries first
    map_object = add_boundaries(map_object, config)

    #Draw routes for each route
    for _, row in route_df.iterrows():
        try:
            route_coords = eval(row["Route Coordinates"]) if isinstance(row["Route Coordinates"], str) else row["Route Coordinates"]
            if not route_coords or len(route_coords) < 2:
                continue

            folium.PolyLine(
                locations=route_coords,
                color="purple",
                weight=3,
                opacity=0.7,
                tooltip=f"{row['Start Postcode']} → {row['Mode']} ({row['Distance (miles)']:.2f} mi)"
            ).add_to(map_object)

            #add a marker at the start postcode
            folium.Marker(
                location=route_coords[0],
                 icon=folium.Icon(color="green"),
            popup=f"<b>{row['Start Postcode']}</b><br>{row['Target']}<br>{row['Mode']}<br>{row['Distance (miles)']:.2f} miles"
            ).add_to(map_object)

        except Exception as e:
            print(f"Failed to render route for {row['Start Postcode']}: {e}")
            continue

    return map_object


def add_red_green_closest_zone_markers(map_object, df_city_centre, df_shopping, selected_area_type, selected_mode):
    """
    Adds red/green markers based on proximity to selected area type.
    - Green: if closer to selected type
    - Red: if Closer to other type
    """
    if df_city_centre.empty or df_shopping.empty:
        print("Missing route data.")
        return map_object

    # Determine route sets
    city_routes = df_city_centre[df_city_centre["Mode"] == selected_mode]
    shop_routes = df_shopping[df_shopping["Mode"] == selected_mode]

    all_postcodes = set(city_routes["Start Postcode"]).union(set(shop_routes["Start Postcode"]))

    for postcode in all_postcodes:
        city_row = city_routes[city_routes["Start Postcode"] == postcode]
        shop_row = shop_routes[shop_routes["Start Postcode"] == postcode]

        city_dist = float(city_row["Distance (miles)"].values[0]) if not city_row.empty else float("inf")
        shop_dist = float(shop_row["Distance (miles)"].values[0]) if not shop_row.empty else float("inf")

        if selected_area_type == "City Centre":
            is_closer = city_dist < shop_dist
        else:
            is_closer = shop_dist < city_dist

        marker_color = "green" if is_closer else "red"
        row = city_row if is_closer or city_row.empty else shop_row
        coords = eval(row["Route Coordinates"].values[0])[0] if not row.empty else None

        if coords:
            folium.Marker(
                location=coords,
                icon=folium.Icon(color=marker_color),
                popup=f"{postcode} ({selected_mode}, {city_dist:.2f} vs {shop_dist:.2f})"
            ).add_to(map_object)

    return map_object



##region Busnet4:


def display_busnet_route_on_map(map_object, route_summary, gStops, start_coords=None, end_coords=None):
    """
    Draws the full multimodal route from BusNet4 onto the map.
    Includes walking, bus and the stops the bus passes by connecting actual stop coordinates.
    """

    status, time_minutes, journey, desc = route_summary
    if status != "found":
        print("No route found.")
        return map_object

    start_linked_stop = next((journey[i + 1] for i in range(len(journey) - 1) if journey[i] == "start"), None)
    end_linked_stop = next((journey[i - 1] for i in range(1, len(journey)) if journey[i] == "end"), None)

    if start_coords:
        folium.Marker(
            location=start_coords,
            popup="Journey Start",
            icon=folium.Icon(color="green", icon="play")
        ).add_to(map_object)
    if end_coords:
        folium.Marker(
            location=end_coords,
            popup="Journey End",
            icon=folium.Icon(color="red", icon="stop")
        ).add_to(map_object)

    if start_coords and start_linked_stop in bus.G.nodes:
        lat2, lon2 = bus.G.nodes[start_linked_stop]["stop_lat"], bus.G.nodes[start_linked_stop]["stop_lon"]
        d = bus.haversine(start_coords[0], start_coords[1], lat2, lon2) * 1000
        t = max((d * bus.walk_speed_ms) / 60, 1)
        folium.PolyLine([(start_coords), (lat2, lon2)], color="blue", weight=3,
                        tooltip=f"Walk to stop: {round(t, 1)} min").add_to(map_object)

    if end_coords and end_linked_stop in bus.G.nodes:
        lat1, lon1 = bus.G.nodes[end_linked_stop]["stop_lat"], bus.G.nodes[end_linked_stop]["stop_lon"]
        d = bus.haversine(lat1, lon1, end_coords[0], end_coords[1]) * 1000
        t = max((d * bus.walk_speed_ms) / 60, 1)
        folium.PolyLine([(lat1, lon1), end_coords], color="blue", weight=3,
                        tooltip=f"Walk to destination: {round(t, 1)} min").add_to(map_object)

    passed_stops = set()

    for idx, node in enumerate(journey):
        if node not in bus.G.nodes:
            continue

        node_type = bus.G.nodes[node]["type"]

        if node_type == "stop":
            lat = bus.G.nodes[node]["stop_lat"]
            lon = bus.G.nodes[node]["stop_lon"]
            stop_name = bus.G.nodes[node]["stop_name"]
            label = f"{node}<br>{stop_name}"

            # Circle marker for stops
            folium.CircleMarker(location=(lat, lon), radius=4, color="black", fill=True,
                                fill_opacity=0.7, popup=label).add_to(map_object)
            passed_stops.add(node)

            if idx > 0 and journey[idx - 1] in bus.G.nodes and bus.G.nodes[journey[idx - 1]]["type"] == "stop":
                prev = journey[idx - 1]
                lat1, lon1 = bus.G.nodes[prev]["stop_lat"], bus.G.nodes[prev]["stop_lon"]
                t = bus.G.edges.get((prev, node), {}).get("time", 0)
                folium.PolyLine([(lat1, lon1), (lat, lon)], color="blue", weight=3,
                                tooltip=f"Walk: {round(t, 1)} min").add_to(map_object)

        elif node_type == "route" and idx > 0 and idx < len(journey) - 1:
            board = journey[idx - 1]
            disembark = journey[idx + 1]
            if board not in bus.G.nodes or disembark not in bus.G.nodes:
                continue

            route_label = node.split(":", 1)[-1]
            stops = bus.G.nodes[node]["route"]
            segment = []
            onboard = False
            time_accum = 0

            for stop_from, stop_to, sec, _ in stops:
                if stop_from == board:
                    onboard = True
                if onboard:
                    if stop_from in bus.G.nodes and stop_to in bus.G.nodes:
                        lat1 = bus.G.nodes[stop_from]["stop_lat"]
                        lon1 = bus.G.nodes[stop_from]["stop_lon"]
                        lat2 = bus.G.nodes[stop_to]["stop_lat"]
                        lon2 = bus.G.nodes[stop_to]["stop_lon"]
                        segment.append(((lat1, lon1), (lat2, lon2), sec))
                        time_accum += sec

                        # Circle markers for passed stops too along the route.
                        for sid in [stop_from, stop_to]:
                            if sid not in passed_stops:
                                slat, slon = bus.G.nodes[sid]["stop_lat"], bus.G.nodes[sid]["stop_lon"]
                                sname = bus.G.nodes[sid]["stop_name"]
                                folium.CircleMarker(location=(slat, slon), radius=4, color="black", fill=True,
                                                    fill_opacity=0.7,
                                                    popup=f"{sid}<br>{sname}").add_to(map_object)
                                passed_stops.add(sid)

                    if stop_to == disembark:
                        break

            for lat1, lon1, lat2, lon2, t in [(a[0][0], a[0][1], a[1][0], a[1][1], a[2]) for a in segment]:
                folium.PolyLine([(lat1, lon1), (lat2, lon2)], color="orange", weight=5,
                                tooltip=f"{route_label} ({round(t/60, 1)} min)").add_to(map_object)

            # Pin marker at bus embarkment
            blat = bus.G.nodes[board]["stop_lat"]
            blon = bus.G.nodes[board]["stop_lon"]
            bname = bus.G.nodes[board]["stop_name"]
            folium.Marker(location=(blat, blon),
                          popup=f"Board<br>{bname}",
                          icon=folium.Icon(color="purple", icon="arrow-up", prefix="fa")).add_to(map_object)

            # Pin marker at disembarkment with total time
            dlat = bus.G.nodes[disembark]["stop_lat"]
            dlon = bus.G.nodes[disembark]["stop_lon"]
            dname = bus.G.nodes[disembark]["stop_name"]
            folium.Marker(location=(dlat, dlon),
                          popup=f"Disembark<br>{dname}<br>Total bus time: {round(time_accum/60, 1)} min",
                          icon=folium.Icon(color="orange", icon="bus", prefix="fa")).add_to(map_object)

    print(f"Route plotted with {len(journey)} points. Total time: {time_minutes:.1f} min.")
    return map_object


#endregion 
