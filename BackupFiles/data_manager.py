# This file handles the loading of different forms of data,: The "city" parameter should ideally be changed to config for most places and only be "city" for the initial load
import pandas as pd
import json
import importlib.util
import os
from shapely.geometry import shape, Point

def load_city_config(city):
    """
    Loads the config file for the selected city.
    city: The selected city name (folder name).
    returns The imported config module if available.
    """
    config_path = f"/content/drive/MyDrive/CityDataNotebook/data/{city.lower()}/config.py"

    if not os.path.exists(config_path):
        print(f"Error: Config file not found for {city} at {config_path} \n please check this file exists and is named properly (i.e config.py)")
        return None

    try:
        spec = importlib.util.spec_from_file_location("config", config_path)
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
        print(f"Successfully loaded config for {city}")
        return config
    except Exception as e:
        print(f"Error: Unable to load configuration for {city}. Details: {e}")
        return None

def load_csv(file_path):
    """
    Loads a CSV file.
    file_path: Path to the CSV file.
    city: City name (for logging purposes).
    description: Description of the data thats being loaded.
    """
    if not os.path.exists(file_path):
        print(f"Error: file not found at {file_path}")
        return None

    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        print(f"Error: Unable to load. Details: {e}")
        return None

def load_json(file_path, city, description="JSON Data"):
    """
    Loads a JSON file.
    file_path: Path to the JSON file.
    city: City name.
    description: Description of the data being loaded.
    """
    if not os.path.exists(file_path):
        print(f"Error: {description} file not found for {city} at {file_path}")
        return None

    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error: Unable to load {description} for {city}. Details: {e}")
        return None

def load_postcodes(config):
    """
    Loads the postcode dataset for the selected city.
    - config: The city config module.
    - Returns: Cleaned DataFrame for valid Latitude/Longitude.
    """
    if not config or not hasattr(config, "pc_dundeePostcodes"):
        print("Error: Postcode dataset path not found in config.")
        return None

    df = load_csv(config.pc_dundeePostcodes)

    if df is None:
        return None  # Return early if data couldnt be loaded

    # Lat/Long exist
    if not {"Postcode", "Latitude", "Longitude"}.issubset(df.columns):
        print("Error: Required columns missing in Postcode dataset.")
        return None

    # Convert to numeric and drop invalid locations
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df = df.dropna(subset=["Latitude", "Longitude"])  # Drop rows with invalid coordinates

    print(f"Loaded {len(df)} valid postcodes for {config.CITY_NAME}, keeping all columns.")
    return df

#TODO: city boundary and city centre boundary can become one function
def load_city_boundary(config):
    """
    Loads the city boundary JSON.
    """
    if not config or not hasattr(config, "b_cityBoundry_path"):
        print("Error: City boundary path not found in config.")
        return None

    return load_json(config.b_cityBoundry_path, config.CITY_NAME, "City Boundary")

def load_city_centre_boundary(config):
    """
    Loads the city centre boundary JSON.
    """
    if not config or not hasattr(config, "b_cityCentre_path"):
        print("Error: City centre boundary path not found in config.")
        return None

    return load_json(config.b_cityCentre_path, config.CITY_NAME, "City Centre Boundary")

def load_filtered_postcodes(config, boundary_type):
    """
    Loads and filters postcodes to include only those inside boundary(s).
    
    Parameters:
    - config: The city config file.
    - boundary_type: The boundary to filter postcodes within.

    Returns:
    - DataFrame containing postcodes within boundary(s).
    """
    if config is None:
        print("Error: No city selected.")
        return None

    print(f"Loading and filtering postcodes for {boundary_type}...")

    # Load full postcode dataset
    df_postcodes = load_postcodes(config)

    if df_postcodes is None or df_postcodes.empty:
        print("No valid postcodes found.")
        return None

    # Load selected boundary
    boundary_path = getattr(config, boundary_type, None)

    if not boundary_path or not os.path.exists(boundary_path):
        print(f"Boundary file not found at {boundary_path}")
        return None

    try:
        with open(boundary_path, "r") as f:
            boundary_data = json.load(f)

        # Convert boundary features to multi polygon
        all_boundaries = [shape(feature["geometry"]) for feature in boundary_data["features"]]

        # Function to check if a postcode is inside any boundary
        def is_inside_any_boundary(lat, lon):
            point = Point(lon, lat)
            return any(boundary.contains(point) for boundary in all_boundaries)

        # Filter postcodes that are inside boundary(s)
        df_inside_boundaries = df_postcodes[df_postcodes.apply(
            lambda row: is_inside_any_boundary(row["Latitude"], row["Longitude"]), axis=1
        )]

        print(f"Found {len(df_inside_boundaries)} postcodes inside {boundary_type}.")
        return df_inside_boundaries

    except Exception as e:
        print(f"Error loading boundary data: {e}")
        return None

def load_affluence_postcodes(config):
    """
    Loads and filters postcodes for affluence.
    TODO:: Change config pc variable name to be more flexible(rather than Dundee).
    Parameters:
    - config: The city configuration.

    Returns:
    - DataFrame containing filtered postcodes with affluence scores.
    """
    if config is None:
        print("Error: No city selected.")
        return None

    # Load the full dataset
    df = pd.read_csv(config.pc_dundeePostcodes)

    # Check required columns exist
    required_columns = ["Postcode", "Latitude", "Longitude", "Population", "Households", "Index of Multiple Deprivation", "In Use?"]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        print(f"Error: Missing columns in dataset: {missing_columns}")
        return None

    # Remove any invalid postcodes (zero population or not in use)
    df = df[(df["Population"] > 0) & (df["In Use?"] != "No")]

    # Normalize deprivation values
    min_deprivation = df["Index of Multiple Deprivation"].min()
    max_deprivation = df["Index of Multiple Deprivation"].max()
    df["Affluence Score"] = 1 - (df["Index of Multiple Deprivation"] - min_deprivation) / (max_deprivation - min_deprivation)
    df["Affluence Score"] = df["Affluence Score"].fillna(0)

    print(f"Loaded {len(df)} valid postcodes with affluence data.")

    return df
