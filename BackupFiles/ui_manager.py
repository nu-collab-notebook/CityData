# this file handles displaying ui elements for the cells such as drop down menues and buttons for users to interact with.
import ipywidgets as widgets
from IPython.display import display

def display_boundary_dropdown(config):
    """
    Creates a dropdown UI for selecting a boundary.

    Parameters:
    - config: The city config file.

    Returns:
    - A drop down for boundary selection.
    """
    if config is None:
        print("Error: No city selected.")
        return None

    available_boundaries = {
        attr.replace("b_", "").replace("_", " ").title(): attr
        for attr in dir(config) if attr.startswith("b_")
    }

    if not available_boundaries:
        print("No boundaries found for this city.")
        return None

    default_boundary = next(iter(available_boundaries.values()), None)

    return widgets.Dropdown(
        options=available_boundaries,
        value=default_boundary,
        description="Boundary:",
    )

def display_accept_button():
    """
    Creates an accept button to confirm selection.

    Returns:
    - A button for user confirmation.
    """
    return widgets.Button(description="Accept", button_style="success")

def get_ui_elements(config):
    """
    Groups all UI elements needed for boundary selection.

    Parameters:
    - config: The city config file.

    Returns:
    - A tuple containing (dropdown, accept button).
    """
    boundary_dropdown = display_boundary_dropdown(config)
    accept_button = display_accept_button()

    return boundary_dropdown, accept_button

def display_toggle():
    """
    Creates a toggle switch to enable/disable boundary inclusion.

    Returns:
    - A checkbox object to toggle boundary inclusion.
    """
    return widgets.Checkbox(value=False, description="Include Boundary")
    
def display_ui_for_heatmap(config):
    """
    Builds UI for selecting optional boundaries to include with the heatmap.

    Parameters:
    - config: The city configuration.

    Returns:
    - A tuple containing the dropdown, toggle, and accept button.
    """
    boundary_dropdown = display_boundary_dropdown(config)
    toggle = display_toggle()
    accept_button = widgets.Button(description="Apply", button_style="success")

    return boundary_dropdown, toggle, accept_button