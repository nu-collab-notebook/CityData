# This file handles the notebook setup, city selection, and config loading.
import os
import ipywidgets as widgets
from ipywidgets import Dropdown, Output, VBox
from pythonScripts import data_manager, map_renderer, cell_manager

#extra imports for cells
from IPython.display import  clear_output
import json
from shapely.geometry import shape, Point


# Path to the data folder (where each city dataset exists)
DATA_FOLDER_PATH = "/content/drive/MyDrive/CityDataNotebook/data"

def get_available_cities():
    """Scans the 'data' folder and returns available city names dynamically."""
    if not os.path.exists(DATA_FOLDER_PATH):
        print(f"Error: Data folder not found at {DATA_FOLDER_PATH}")
        return []

    # List city folders inside the data directory
    return [folder for folder in os.listdir(DATA_FOLDER_PATH) if os.path.isdir(os.path.join(DATA_FOLDER_PATH, folder))]

# **Dropdown UI for selecting a city**
available_cities = get_available_cities()
city_selector = Dropdown(
    options=available_cities,
    value=available_cities[0] if available_cities else None,  # Default to the first available city
    description="City:",
)

config_output = Output()  # Output widget for displaying config status

def choose_city():
    """Returns the currently selected city."""
    return city_selector.value

def load_city_config():
    """Loads and returns the config for the selected city."""
    with config_output:
        config_output.clear_output()
        selected_city = choose_city()

        if selected_city:
            print(f"Loading config for {selected_city}...")
            return data_manager.load_city_config(selected_city)  # Load the config file

        print("⚠ No city selected.")
        return None

def build_ui():
    """Builds the UI for selecting a city."""
    return VBox([city_selector, config_output])

def initialize_notebook():
    """Sets up the notebook environment (UI + Config)."""
    display(build_ui())  # Display UI
    config = load_city_config()  # Load default config
    return config
