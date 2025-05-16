# This file is for adding and removing markers with potential for more, currently adding markers is not very user friendly so will need to revisit this
from ipyleaflet import Map, Marker, MarkerCluster
from ipywidgets import Output, Select, Layout


# UI Output
marker_output = Output()

# Initialize marker cluster
marker_cluster = MarkerCluster(markers=[])

# Store active markers
placed_markers = {}  # Dictionary to store markers with names
marker_locations = []  # Store marker coordinates
pending_marker = None  # Temporary marker that follows the mouse (Bit janky at the moment)

# Marker selection UI
marker_list = Select(options=[], description="Markers", layout=Layout(width="250px", height="100px"))

def update_marker_list():
    """ Updates the dropdown list of markers. """
    marker_list.options = list(placed_markers.keys())

def refresh_marker_cluster(map_obj):
    """ Ensure markers update properly. """
    map_obj.remove_layer(marker_cluster)
    map_obj.add_layer(marker_cluster)

def add_marker(map_obj, config):
    """ 
    Starts marker placement: A temporary marker appears at the city center and follows the mouse.
    """
    global pending_marker

    if len(placed_markers) >= 2:
        with marker_output:
            print("Limit reached: Only two markers allowed.")
        return

    marker_name = f"Marker {len(placed_markers) + 1}"

    # Load city config to get the center
   # config = data_manager.load_city_config(city)
    if config is None:
        with marker_output:
            print(f"Error: Could not load configuration for {config.CITY_NAME}.")
        return

    # Create a temporary marker at the city center
    pending_marker = Marker(location=config.CENTRE, draggable=True)
    map_obj.add_layer(pending_marker)

    with marker_output:
        print(f"Move the mouse to position {marker_name}, then click to place.")

def confirm_marker_placement(map_obj, **kwargs):
    """ 
    Finalizes marker placement when the user clicks on the map.
    """
    global pending_marker

    if pending_marker is None:
        return  # No pending marker to place

    if "coordinates" in kwargs:
        location = kwargs["coordinates"]
        marker_name = f"Marker {len(placed_markers) + 1}"

        # Replace temporary marker with permanent marker
        new_marker = Marker(location=location, draggable=True)

        # Ensure marker moves are tracked properly
        new_marker.on_move(lambda **args: update_marker_position(new_marker, args.get("location", location)))

        # Store the new marker
        placed_markers[marker_name] = new_marker
        marker_locations.append(location)

        # Refresh UI & remove temp marker
        marker_cluster.markers = list(placed_markers.values())
        update_marker_list()
        refresh_marker_cluster(map_obj)
        map_obj.remove_layer(pending_marker)
        pending_marker = None

        with marker_output:
            print(f"{marker_name} placed at: {location}")

    # Debugging: Print latest marker locations
    print("Final marker locations after placement:", marker_locations)

def update_marker_position(marker, location):
    """ Updates the marker's position when moved. """
    for name, m in placed_markers.items():
        if m == marker:
            # Remove old location from marker_locations
            if m.location in marker_locations:
                marker_locations.remove(m.location)

            # Store the new marker location
            marker_locations.append(location)
            m.location = location  # Ensure the marker object itself updates

            with marker_output:
                print(f"Moved {name} to {location}")

    # Debugging: Confirm the function is being called
    print("🔄 Updated marker locations:", marker_locations)

def delete_selected_marker(map_obj):
    """ Deletes the selected marker and refreshes the map. """
    selected_marker_name = marker_list.value
    if selected_marker_name in placed_markers:
        marker = placed_markers.pop(selected_marker_name)
        if marker and marker.location in marker_locations:
            marker_locations.remove(marker.location)
        marker_cluster.markers = list(placed_markers.values())
        update_marker_list()
        refresh_marker_cluster(map_obj)

        with marker_output:
            print(f"🗑 Removed {selected_marker_name}")
    else:
        with marker_output:
            print("⚠ Error: Selected marker not found.")
