from langchain_core.tools import tool
from typing import Optional

from predict import predict_yield

@tool
def predict_yield_tool(item: str, year: int, area_harvested: Optional[float] = None) -> dict:
    """
    Predict crop yield (kg/ha) for India given a crop name and year.
 
    Use this when the user asks about expected/likely yield, output per
    hectare, or productivity for a specific crop and year. Do NOT use it for
    total production volume, fertilizer demand, or soil/weather questions -
    those belong to the other models in this system.
 
    Args:
        item: Crop name exactly as used in the FAOSTAT India dataset, e.g.
            "Rice", "Wheat", "Sugar cane". If unsure of the exact name, call
            with your best guess first - on failure this tool returns the
            full list of valid names to choose from.
        year: Year to predict for (e.g. 2025). Years beyond the underlying
            fertilizer/soil/temperature data availability fall back to the
            closest available year's context - this is noted in the result.
        area_harvested: Optional area harvested in hectares. If omitted,
            this crop's historical median is used.
 
    Returns:
        A dict with `ok: bool`. On success: `predicted_yield_kg_ha`,
        `low_kg_ha`, `high_kg_ha` (the crop-specific confidence range),
        `typical_error_pct`, `low_confidence` (True if this crop had too
        little held-out test data to trust its own error rate), and `notes`
        (any caveats applied, e.g. a fallback year or default area used).
        On failure: `error` and `valid_items` (the full crop name list, so
        the agent can retry with the correct spelling instead of giving up).
    """
    return predict_yield(item=item, year=year, area_harvested=area_harvested)