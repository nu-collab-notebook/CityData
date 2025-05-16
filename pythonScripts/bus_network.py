# this file should be removed.
import json
from haversine import haversine

class BusNetwork:
    def __init__(self, file_path):
        """Loads the bus stop data from a GeoJSON file."""
        with open(file_path, "r") as file:
            data = json.load(file)

        self.stops = [
            {
                "name": feature["properties"]["name"],
                "loc": tuple(feature["geometry"]["coordinates"][::-1]),  # Convert to lat lon
                "routes": feature["properties"].get("routes", [])
            }
            for feature in data["features"]
        ]

        print(f"Loaded {len(self.stops)} bus stops.")

    def find_closest_stop(self, location):
        """Finds the closest bus stop to a given location."""
        if not self.stops:
            print(" No bus stops available.")
            return None
        return min(self.stops, key=lambda stop: haversine(location, stop['loc']), default=None)



    from haversine import haversine

    def calculate_route(self, loc1, loc2, foot_router, car_router):
        """Calculates the bus route and walk distances."""
        start_stop = self.find_closest_stop(loc1)
        end_stop = self.find_closest_stop(loc2)

        if not start_stop or not end_stop:
            print("No valid bus stops found.")
            return False, "", 0, 0, []

        walk1 = foot_router.route(loc1, start_stop["loc"])[1]
        walk2 = foot_router.route(loc2, end_stop["loc"])[1]
        status, bus_distance, bus_route_coords = car_router.route(start_stop["loc"], end_stop["loc"])

        if -1 in (walk1, walk2, bus_distance):
            print(" Routing failed.")
            return False, "", 0, 0, []

        total_distance = walk1 + walk2 + bus_distance
        full_route = [loc1, start_stop["loc"]] + bus_route_coords + [end_stop["loc"], loc2]

        return True, start_stop["routes"], walk1 + walk2, bus_distance, full_route

