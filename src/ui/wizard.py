import questionary
from typing import Dict, Any


def run_scan_wizard() -> Dict[str, Any]:
    """
    Run an interactive wizard to configure scan parameters.
    Returns a dictionary of selected parameters.
    """
    config = {}

    # 1. Select active filters
    choices = [
        questionary.Choice("Minimum Price", value="min_price"),
        questionary.Choice("Minimum Volume", value="min_volume"),
        questionary.Choice("Relative Volume (RVOL)", value="min_relative_volume"),
        questionary.Choice("ADR %", value="min_adr"),
        questionary.Choice("Gap Up %", value="gap_up"),
        questionary.Choice("Trend Template (Minervini)", value="trend_template"),
    ]

    selected_filters = questionary.checkbox(
        "Select filters to apply:", choices=choices
    ).ask()

    if selected_filters is None:
        return {}

    # 2. Ask for values for selected filters
    if "min_price" in selected_filters:
        config["min_price"] = float(
            questionary.text("Minimum Price ($):", default="10.0").ask()
        )

    if "min_volume" in selected_filters:
        config["min_volume"] = float(
            questionary.text("Minimum Volume:", default="1000000").ask()
        )

    if "min_relative_volume" in selected_filters:
        config["min_relative_volume"] = float(
            questionary.text("Minimum RVOL (e.g., 1.5):", default="1.5").ask()
        )

    if "min_adr" in selected_filters:
        config["min_adr"] = float(
            questionary.text("Minimum ADR % (e.g., 3.5):", default="3.5").ask()
        )

    if "gap_up" in selected_filters:
        config["gap_up"] = float(
            questionary.text("Minimum Gap Up % (e.g., 2.0):", default="2.0").ask()
        )

    if "trend_template" in selected_filters:
        config["trend_template"] = True

    # 3. Sort preference
    sort_choices = [
        questionary.Choice("Symbol (Default)", value="symbol"),
        questionary.Choice("Close Price", value="close"),
        questionary.Choice("Volume", value="volume"),
        questionary.Choice("RVOL", value="rvol_20"),
        questionary.Choice("ADR %", value="adr_20"),
    ]

    sort_col = questionary.select(
        "Sort results by:",
        choices=sort_choices,
        default=sort_choices[0],
    ).ask()

    config["sort"] = sort_col

    return config
