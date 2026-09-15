"""
LangGraph/LangChain tool wrapper for the market price forecaster.
Same pattern as yield_tool.py and weather_tool.py.
"""

from langchain_core.tools import tool
from predict import predict_price


@tool
def predict_price_tool(item: str, year: int) -> dict:
    """
    Forecast the Producer Price Index level for a crop in India for a given
    year. This is the 3rd node in the pipeline - it runs sequentially AFTER
    the yield + weather aggregation, and its output feeds the supply chain
    optimizer next.

    Use this when the user asks about price trends, expected market price,
    or price forecasts for a specific crop and year. This is an INDEX value
    (base 100 = 2014-2016 average), not a currency amount - if the user
    wants actual currency prices, say so rather than presenting the index
    as if it were LCU/USD.

    Args:
        item: Crop name exactly as used in the FAOSTAT India price dataset,
            e.g. "Rice", "Wheat", "Cotton seed". On an unknown name, this
            tool returns the full valid list so you can retry.
        year: Year to forecast. Years at or before the last known data
            point return the actual historical value (`is_historical: True`)
            rather than a forecast. Years beyond it are forecast by
            recursively compounding a predicted year-over-year growth rate -
            accuracy degrades the further out you go, reflected in a
            widening `low_index_level`/`high_index_level` range.

    Returns:
        A dict with `ok: bool`. On success: `predicted_index_level`,
        `is_historical`, and (for forecasted years only) `low_index_level`,
        `high_index_level`, `typical_error_pp`, `steps_ahead`,
        `low_confidence`, `notes`. On failure: `error` (and `valid_items`
        for an unknown crop name).
    """
    return predict_price(item=item, year=year)