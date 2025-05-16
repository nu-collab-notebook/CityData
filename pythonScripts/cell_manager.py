# This File handles running of cells to takee the bulk code out of the notebook.

import ipywidgets as widgets
from IPython.display import display
from pythonScripts import data_manager, map_renderer, ui_manager, routing_manager, bus_network
from google.colab import output
import pandas as pd

#region Postcodes

def run_boundary_postcode_selection(config):
    """
    Manages filtering postcodes based on boundary selection and renders the map dynamically.
    
    Parameters:
    - config: The city configuration.
    
    Displays:
    - A UI dropdown for selecting a boundary.
    - An accept button to confirm selection.
    - Automatically filters postcodes and updates the map based on selection.
    """
    if config is None:
        print("Error: No city selected.")
        return

    # Get UI elements (dropdown + accept button)
    boundary_selector, accept_button = ui_manager.get_ui_elements(config)

    # Output widget to display the map
    map_output = widgets.Output()

    def update_map(_):
        """Filters postcodes based on selected boundary and updates the map with the selected boundary."""
        selected_boundary = boundary_selector.value
        df_filtered = data_manager.load_filtered_postcodes(config, selected_boundary)

        with map_output:
            map_output.clear_output()
            if df_filtered is not None:
                display(
                    map_renderer.combine_map_layers(
                        config,
                        lambda m: map_renderer.add_selected_boundary(m, config, selected_boundary),# this is for showing the selected boundary
                        lambda m: map_renderer.add_postcode_markers(m, df_filtered) # this is for showing just the filtered postcodes

                    )
                )
            else:
                print(f"No postcodes found for {selected_boundary}.")

    # Attach event listener to the accept button
    accept_button.on_click(update_map)

    # Display UI elements and the map output
    display(boundary_selector, accept_button, map_output)

def run_heatmap_with_boundaries(config):
    """
    Allows users to select a boundary to display with the heatmap.
    Users can toggle to include boundaries and apply changes dynamically.

    Parameters:
    - config: The city configuration.

    Displays:
    - A UI dropdown for selecting boundaries.
    - A toggle switch for enabling/disabling the boundary.
    - An accept button to confirm selection.
    - Generates a map with the selected boundary and heatmap.
    """
    if config is None:
        print("Error: No city selected.")
        return

    # Get UI elements (boundary selector, toggle, heatmap selector, accept button)
    boundary_selector, boundary_toggle, heatmap_selector, accept_button = ui_manager.display_ui_for_heatmap(config)

    # Output widget for map display
    map_output = widgets.Output()

    def update_map(_):
        """Updates the heatmap and boundary selection based on user input."""
        selected_boundary = boundary_selector.value
        include_boundary = boundary_toggle.value
        selected_heatmap = heatmap_selector.value

        print(f"🔄 Loading {selected_heatmap} heatmap with boundary: {selected_boundary if include_boundary else 'None'}")

        df_selected = data_manager.load_affluence_postcodes(config) # may need to change naming here and deeper into datamanager for the dynamic changes

        if selected_heatmap == "Affluence":
            column_name = "Index of Multiple Deprivation"
            label = "Affluence Scale"
        elif selected_heatmap == "Population":
            column_name = "Population"
            label = "Population Density"
        else:
            column_name = "Households"
            label = "Household Density"

        with map_output:
            map_output.clear_output()
            if df_selected is not None:
                m = map_renderer.generate_base_map(config)
                m = map_renderer.add_dynamic_heatmap(m, df_selected, column_name, label)
                m = map_renderer.add_dynamic_markers(m, df_selected, column_name)

                # Add the selected boundary if enabled
                if include_boundary and selected_boundary is not None:
                    m = map_renderer.add_selected_boundary(m, config, selected_boundary)

                display(m)
            else:
                print("No valid postcodes found.")

    # Attach event listener to the accept button
    accept_button.on_click(update_map)

    # Display UI elements and the map output
    display(boundary_selector, boundary_toggle, heatmap_selector, accept_button, map_output)


    ####################################
    ####################################
    ####################################
    ####################################

def getLatLonFromPCode(postcode, df_postcodes):
    """
    Retrieves the latitude and longitude of a given postcode.

    Parameters:
    - `postcode`: The postcode string to search for.
    - `df_postcodes`: The DataFrame containing postcode data.

    Returns:
    - Tuple `(latitude, longitude)` if found, otherwise `None`.
    """

    # Ensure postcode exists in the dataset
    row = df_postcodes[df_postcodes["Postcode"] == postcode]
    
    if row.empty:
        print(f"ERROR: Postcode {postcode} not found in dataset.")
        return None

    return (row["Latitude"].values[0], row["Longitude"].values[0])

#endregion

#############################################################################################################
#############################################################################################################

#region travel

def run_postcode_travel_time_search(config):
    """
    Lets the user enter a postcode, then displays BusNet4 route first,
    followed by walk, cycle, and car routes all on the same map.
    """

    if config is None:
        print("Error: No city selected.")
        return

    # Initialise routers
    footRouter = routing_manager.initialize_router("foot", config.map_osm_gz, "gz")
    cycleRouter = routing_manager.initialize_router("cycle", config.map_osm_gz, "gz")
    carRouter = routing_manager.initialize_router("car", config.map_osm_gz, "gz")

    # Input widgets
    postcode_input = widgets.Text(
        placeholder="Enter postcode (e.g., DD3 0BN)",
        description="Postcode:",
        layout=widgets.Layout(width="300px")
    )

    destination_selector = widgets.Dropdown(
        options=["City Centre", "Shopping Districts"],
        value="City Centre",
        description="Destination:"
    )

    calculate_button = widgets.Button(description="Calculate Routes", button_style="success")
    map_output = widgets.Output()

    def on_calculate(_):
        selected_postcode = postcode_input.value.strip().upper()
        dest_type = destination_selector.value

        if not selected_postcode:
            print("Please enter a postcode.")
            return

        df_postcodes = data_manager.load_affluence_postcodes(config)
        if df_postcodes is None or df_postcodes.empty:
            print("Postcode data not found.")
            return

        dest_df = (
            data_manager.load_csv(config.pc_cityCentre)
            if dest_type == "City Centre"
            else data_manager.load_csv(config.pc_shopping)
        )

        if dest_df is None or dest_df.empty:
            print(f"Destination data for {dest_type} is unavailable.")
            return

        # Get coordinates
        start_coords = data_manager.getLatLonFromPCode(selected_postcode, df_postcodes)
        if not start_coords:
            return
        end_coords = routing_manager.find_nearest_destination(start_coords, dest_df)
        if not end_coords:
            return

        with map_output:
            map_output.clear_output()

            # start first with BusNet4 routing 
            print(f"Drawing BusNet4 route from {start_coords} to {end_coords}")
            m = map_renderer.generate_base_map(config)

            route_summary = bus.findPath(start_coords, end=end_coords, walk=0.5)
            if route_summary[0] == "found":
                m = map_renderer.display_busnet_route_on_map(m, route_summary, bus.gStops, start_coords, end_coords)
            else:
                print("⚠ BusNet4 route not found.")

            # add routes
            distances, routes = routing_manager.calculate_distances_and_routes(
                selected_postcode,
                df_postcodes,
                dest_df,
                footRouter,
                cycleRouter,
                carRouter
            )

            data_manager.save_route_data(dest_type, selected_postcode, distances, routes)

            m = map_renderer.display_routes_on_map(m, routes)
            map_renderer.add_route_legend(m)

            # display the final combined map
            display(m)

    calculate_button.on_click(on_calculate)
    display(postcode_input, destination_selector, calculate_button, map_output)





#TODO::need to refactor this one to use ui manager and initialise routers seperatly
def run_closest_postcode_to_commercial_view(config):
    """
    Displays only postcodes closest to the selected commercial zones
    """

    # Dropdowns
    destination_dropdown = widgets.Dropdown(
        options=["City Centre", "Shopping Districts"],
        value="City Centre",
        description="Area:"
    )

    mode_dropdown = widgets.Dropdown(
        options=["Walking", "Cycling", "Driving"],
        value="Walking",
        description="Mode:"
    )

    run_button = widgets.Button(description="Accept", button_style="success")
    map_output = widgets.Output()

    def update_map(_):
        selected_dest = destination_dropdown.value
        selected_mode = mode_dropdown.value

        # Load both route CSVs
        df_shopping = data_manager.load_routes_csv(config.r_shopping)
        df_city = data_manager.load_routes_csv(config.r_cityCentre)

        # Filter based on mode
        df_shopping = df_shopping[df_shopping["Mode"] == selected_mode]
        df_city = df_city[df_city["Mode"] == selected_mode]

        # Merge and compare distances
        merged = df_shopping.merge(df_city, on="Start Postcode", suffixes=("_shopping", "_city"))
        closer_shopping = merged[merged["Distance (miles)_shopping"] < merged["Distance (miles)_city"]]
        closer_city = merged[merged["Distance (miles)_city"] < merged["Distance (miles)_shopping"]]

        if selected_dest == "City Centre":
            df = closer_city[["Start Postcode", "Distance (miles)_city", "Route Coordinates_city"]].copy()
            df = df.rename(columns={
                "Distance (miles)_city": "Distance (miles)",
                "Route Coordinates_city": "Route Coordinates"
            })
            df["Target"] = "City Centre"
        else:
            df = closer_shopping[["Start Postcode", "Distance (miles)_shopping", "Route Coordinates_shopping"]].copy()
            df = df.rename(columns={
                "Distance (miles)_shopping": "Distance (miles)",
                "Route Coordinates_shopping": "Route Coordinates"
            })
            df["Target"] = "Shopping District"

        df["Mode"] = selected_mode

        # Display on map
        with map_output:
            map_output.clear_output()
            m = map_renderer.generate_base_map(config)
            m = map_renderer.show_closest_routes_only(config, m, df)
            display(m)

    run_button.on_click(update_map)
    display(destination_dropdown, mode_dropdown, run_button, map_output)



def run_closest_zone_red_green_visualization(config):
    """
    Displays markers as red or green based on which zone (City Centre or Shopping District) is closer.
    """

    # Dropdown for zone type
    zone_selector = widgets.Dropdown(
        options=["City Centre", "Shopping Districts"],
        value="City Centre",
        description="Area Type:"
    )

    # Dropdown for mode
    mode_selector = widgets.Dropdown(
        options=["Walking", "Cycling", "Driving"],
        value="Walking",
        description="Mode:"
    )

    # Button
    display_button = widgets.Button(description="Display Map", button_style="success")
    map_output = widgets.Output()

    def on_display(_):

        df_city = pd.read_csv(config.r_cityCentre)
        df_shop = pd.read_csv(config.r_shopping)

        with map_output:
            map_output.clear_output()
            m = map_renderer.generate_base_map(config)
            m = map_renderer.add_boundaries(m, config)

            m = map_renderer.add_red_green_closest_zone_markers(
                m,
                df_city,
                df_shop,
                zone_selector.value,
                mode_selector.value
            )

            display(m)

    display_button.on_click(on_display)

    # Show UI
    display(zone_selector, mode_selector, display_button, map_output)



#endregion


#region busnet4
#(once busnet4 is confirmed to be clear we can clean up and modularise this region)

# Imports all needed for BusNet4 
import networkx as nx
import pandas as pd
import geopandas
from datetime import datetime
import numpy as np
import sys
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, LineString, Point
from IPython.display import clear_output
import pickle
import math
import time
import json


from pythonScripts import BusNet4 as bus

# Create a bounding box for the area that we're interested in
def initialise_busnetfour():
  
    j = json.load(open('/content/drive/MyDrive/CityDataNotebook/data/dundee/boundaries/dundee_boundaries.geojson'))
    j = j['features'][0]
    coords = j['geometry']['coordinates'][0]
    dundeeBoundary = []
    for c in coords:
        dundeeBoundary.append(Point(c[1],c[0]))

    bus.setup(cache="/content/drive/MyDrive/CityDataNotebook/data/dundee/routes/busnet/dundeeworking",
          validAgency = ["Ember","Stagecoach East Scotland","Moffat & Williamson","Xplore Dundee"],
          boundingPoly = dundeeBoundary)



def bus_route_to_boundary(config):
  # Define city centre polygon
  city_centre = [
      Point(56.45521456343855, -2.975808604),
      Point(56.46084193778188, -2.9768997916807534),
      Point(56.463990223978904, -2.967079106389851),
      Point(56.460239044693814, -2.9604107398342996),
  ]

  # Define start coordinates
  start = (56.470206206351286, -2.989496813513388)

  # Run routing using centre polygon
  r = bus.findPath(start, walk=0.5, centre=city_centre)
  print(r)

  # Display the route on the map
  m = map_renderer.generate_base_map(config)
  m= map_renderer.add_boundaries(m,config)
  m = map_renderer.display_busnet_route_on_map(m, r, bus.gStops, start_coords=start)
  display(m)


def show_route_between_points(start,end,config):
  r = bus.findPath(start, end=end, walk=0.5)

  m = map_renderer.generate_base_map(config)
  m = map_renderer.display_busnet_route_on_map(m, r, bus.gStops, start_coords=start, end_coords=end)
  display(m)


def run_postcode_route_between_selectable_points(config):
    """
    Allows the user to select a start and end postcode from dropdowns and shows the BusNet4 route between them.
    """
    if config is None:
        print("error: no city selected.")
        return

    df = data_manager.load_affluence_postcodes(config)
    if df is None or df.empty:
        print("No postcode data available.")
        return

    postcodes = sorted(df["Postcode"].unique())

    # Dropdowns for selecting postcodes
    start_dropdown = widgets.Dropdown(
        options=postcodes,
        description="Start:",
        layout=widgets.Layout(width="300px")
    )

    end_dropdown = widgets.Dropdown(
        options=postcodes,
        description="End:",
        layout=widgets.Layout(width="300px")
    )

    go_button = widgets.Button(description="Show Route", button_style="success")
    map_output = widgets.Output()

    def on_click(_):
        start_pc = start_dropdown.value
        end_pc = end_dropdown.value

        start_coords = data_manager.getLatLonFromPCode(start_pc, df)
        end_coords = data_manager.getLatLonFromPCode(end_pc, df)

        if not start_coords or not end_coords:
            print("One or both postcodes are invalid.")
            return

        with map_output:
            map_output.clear_output()
            print(f"Showing BusNet4 route from {start_pc} → {end_pc}")
            show_route_between_points(start_coords, end_coords, config)

    go_button.on_click(on_click)
    display(widgets.VBox([start_dropdown, end_dropdown, go_button, map_output]))


#endregion 
