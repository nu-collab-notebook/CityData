from pyroutelib3 import Router
import geopy.distance
import json

# -------------------------------
# Router Initialization
# -------------------------------
def initialize_router(mode, osm_file, file_type):
    """
    Initializes and returns a router for the specified mode.
    """
    class CustomRouter:
        def __init__(self, mode, file_path, file_type):
            self.router = Router(mode, file_path, localfileType=file_type)

        def route(self, start_loc, end_loc):
            """
            Finds the best route between two locations.
            Returns (status, distance, route coordinates) if successful, else (status, -1, []).
            """
            start_node = self.router.findNode(*start_loc)
            end_node = self.router.findNode(*end_loc)

            status, route = self.router.doRoute(start_node, end_node)

            if status != 'success' or not isinstance(route, list) or len(route) == 0:
                print(f"Routing failed between {start_loc} and {end_loc}")
                return status, -1, []

            route_coords = [self.router.nodeLatLon(node) for node in route]
            distance = sum(
                self.router.distance(route_coords[i], route_coords[i+1])
                for i in range(len(route_coords) - 1)
            )

            return status, distance, route_coords

    return CustomRouter(mode, osm_file, file_type)

# -------------------------------
# Find Nearest Destination
# -------------------------------
def find_nearest_destination(start_loc, destination_df):
    """Finds the nearest destination to the selected postcode."""
    validate_coordinates(start_loc, "Start Location")

    destination_list = [
        (float(row["Latitude"]), float(row["Longitude"])) 
        for _, row in destination_df.iterrows()
    ]

    if not destination_list:
        print("ERROR: No valid destination data available!")
        return None

    nearest = min(
        destination_list,
        key=lambda loc: geopy.distance.distance(start_loc, loc).km
    )

    validate_coordinates(nearest, "Nearest Destination")
    print(f"Nearest destination to {start_loc}: {nearest}")
    return nearest

# -------------------------------
# Coordinate Validation
# -------------------------------
def validate_coordinates(location, name="Location"):
    """Ensures that the input is a valid (lat, lon) tuple of floats."""
    if not isinstance(location, tuple) or len(location) != 2:
        raise ValueError(f"{name} is not a valid tuple: {location}")
    if not all(isinstance(coord, (float, int)) for coord in location):
        raise ValueError(f"{name} coordinates must be floats/ints: {location}")

# -------------------------------
# Calculate Distances and Store Routes
# -------------------------------
import geopy.distance

def calculate_distances_and_routes(postcode, df_postcodes, destination_df, foot_router, cycle_router, car_router):
    """
    Calculates distances and routes for different transport modes.
    """

    start_row = df_postcodes[df_postcodes["Postcode"] == postcode]
    if start_row.empty:
        print(f" ERROR: Postcode `{postcode}` not found in dataset.")
        return None, None

    start_loc = (float(start_row["Latitude"].values[0]), float(start_row["Longitude"].values[0]))

    destination_row = destination_df.loc[
        destination_df.apply(lambda row: geopy.distance.distance(start_loc, (row["Latitude"], row["Longitude"])).km, axis=1).idxmin()
    ]
    destination = (float(destination_row["Latitude"]), float(destination_row["Longitude"]))
    destination_postcode = destination_row["Postcode"]

    # Calculate Routes and Distances
    routes = {}
    distances = {}

    for mode, router in zip(["Walking", "Cycling", "Driving"], [foot_router, cycle_router, car_router]):
        status, distance, route_coords = router.route(start_loc, destination)
        distances[mode] = distance * 0.621371 if status == "success" else "No Route"
        routes[mode] = route_coords

    # Bus Route Calculation


    return distances, routes

