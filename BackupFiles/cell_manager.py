# This File handles running of cells to takee the bulk code out of the notebook.

import ipywidgets as widgets
from IPython.display import display
from pythonScripts import data_manager, map_renderer, ui_manager

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
                        lambda m: map_renderer.add_selected_boundary(m, config, selected_boundary),
                        lambda m: map_renderer.add_postcode_markers(m, df_filtered)
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

    # Get UI elements (dropdown + toggle + accept button)
    boundary_selector, boundary_toggle, accept_button = ui_manager.display_ui_for_heatmap(config)

    # Output widget for map display
    map_output = widgets.Output()

    def update_map(_):
        """Updates the heatmap and boundary selection based on user input."""
        selected_boundary = boundary_selector.value
        include_boundary = boundary_toggle.value

        print(f"Loading heatmap with boundary: {selected_boundary if include_boundary else 'None'}")

        df_affluence = data_manager.load_affluence_postcodes(config)

        with map_output:
            map_output.clear_output()
            if df_affluence is not None:
                m = map_renderer.generate_base_map(config)
                m = map_renderer.add_affluence_heatmap(m, df_affluence)
                m = map_renderer.add_affluence_markers(m, df_affluence)

                # Add the selected boundary if enabled
                if include_boundary and selected_boundary is not None:
                    m = map_renderer.add_selected_boundary(m, config, selected_boundary)

                display(m)
            else:
                print("No valid postcodes found.")

    # Attach event listener to the accept button
    accept_button.on_click(update_map)

    # Display UI elements and the map output
    display(boundary_selector, boundary_toggle, accept_button, map_output)