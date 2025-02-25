# This file handles rendering  the map and other map related things such as boundaries and markers. (possibly split the code later once the file is large to modularise the code)
import folium
import json
import os
import pandas as pd
import ipywidgets as widgets
from folium.plugins import MarkerCluster
from IPython.display import display
import matplotlib.colors as mcolors

import geopandas as gpd

from shapely.geometry import shape, Point


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
        #Debug print(f"Adding boundary: {boundary_type}")

        
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



def get_exact_color(imd, min_imd, max_imd):
    """Gets the exact color for both heatmap & markers. used for index of mult deprevation"""
    colormap = mcolors.LinearSegmentedColormap.from_list(
        "deprivation_gradient",
        ["darkred", "#D73027", "#FC8D59", "yellow", "#91CF60", "#1A9850", "lightblue"]
    )

    if pd.isna(imd) or imd == 0:
        return "black"  # Black for missing or zero IMD values
    
    norm_score = (imd - min_imd) / (max_imd - min_imd)
    return mcolors.rgb2hex(colormap(norm_score))  # Convert to hex color

def add_affluence_heatmap(map_object, df):
    """
    Adds a deprivation heatmap.

    Parameters:
    - map_object: The folium map obj.
    - df: DataFrame containing postcodes with deprivation values.

    Returns:
    - The updated folium map with heatmap overlay.
    """
    if df is None or df.empty:
        print("Error: No valid postcode data.")
        return map_object

    print("Adding deprivation heatmap...")

    # Normalize deprivation index for color mapping （will possibly remove normailisation)
    min_imd = df["Index of Multiple Deprivation"].min()
    max_imd = df["Index of Multiple Deprivation"].max()

    heatmap_layer = folium.FeatureGroup(name="Deprivation Heatmap")

    for _, row in df.iterrows():
        lat, lon = float(row["Latitude"]), float(row["Longitude"])
        imd_value = float(row["Index of Multiple Deprivation"])
        exact_color = get_exact_color(imd_value, min_imd, max_imd)

        folium.CircleMarker(
            location=(lat, lon),
            radius=6,
            color=exact_color,
            fill=True,
            fill_color=exact_color,
            fill_opacity=0.3,
            opacity=0.2
        ).add_to(heatmap_layer)

    map_object.add_child(heatmap_layer)
    print("Heatmap added.")
    return map_object

def add_affluence_markers(map_object, df):
    """
    Adds postcode markers with affluence colors.

    Parameters:
    - map_object: The folium map object.
    - df: DataFrame containing postcodes with deprivation values.

    Returns:
    - The updated folium map with postcode markers.
    """
    if df is None or df.empty:
        print("No valid postcode data.")
        return map_object

    print("Adding postcode markers...")

    min_imd = df["Index of Multiple Deprivation"].min()
    max_imd = df["Index of Multiple Deprivation"].max()

    marker_cluster = MarkerCluster(name="Postcode Markers").add_to(map_object)

    for _, row in df.iterrows():
        lat, lon = float(row["Latitude"]), float(row["Longitude"])
        imd_value = float(row["Index of Multiple Deprivation"])
        exact_color = get_exact_color(imd_value, min_imd, max_imd)

        # check markers display real deprivation values
        popup_text = f"<b>{row['Postcode']}</b><br>Population: {int(row['Population'])}<br>Households: {int(row['Households'])}<br>Deprivation Index: {imd_value}"

        folium.Marker(
            location=(lat, lon),
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color="gray", icon="info-sign")
        ).add_to(marker_cluster)

        # Overlay a small colour circle behind the marker
        folium.Circle(
            location=(lat, lon),
            radius=12,
            color=exact_color,
            fill=True,
            fill_color=exact_color,
            fill_opacity=0.8
        ).add_to(map_object)

    print("Postcode markers added.")
    return map_object