"""
LangGraph/LangChain tool wrapper for the supply chain optimizer.
Same pattern as yield_tool.py, weather_tool.py, price_tool.py.
"""

from typing import Optional
from langchain_core.tools import tool
from predict import optimize_supply_chain


@tool
def supply_chain_tool(
    item: str,
    quantity_tonnes: float,
    current_price_per_quintal: float,
    direct_to_market_distance_km: float,
    price_growth_pct_per_month: Optional[float] = None,
) -> dict:
    """
    Decide whether to sell a harvest now or store it, and for how long, to
    maximize profit. This is the 4th and final node - it runs sequentially
    after the price forecaster and consumes its output as
    price_growth_pct_per_month.

    Use this when the user asks about storage vs. selling, logistics cost,
    or expected profit for a harvest. Do NOT use it for "when to harvest"
    or specific routes/warehouses - this system has no crop-calendar or
    real-location data, so it only decides among distances and rates it's
    actually given.

    Args:
        item: Crop name (matches the FAOSTAT India Food Balance Sheet Item
            names, e.g. "Rice and products", "Potatoes and products"). Falls
            back to an all-crop average loss rate if not in the reference
            table - noted in the result.
        quantity_tonnes: Harvest quantity available to sell.
        current_price_per_quintal: TODAY's real ₹/quintal market price.
            Required - the price forecaster gives a growth trend, not a
            currency figure, so the actual current price has to come from
            the caller.
        direct_to_market_distance_km: Distance for the sell-now baseline.
            Real storage option distances/rates can be passed via the
            underlying optimize_supply_chain() function if available;
            this tool uses sensible defaults (FCI + private cold storage
            benchmarks) otherwise, noted in the result.
        price_growth_pct_per_month: Pass the price forecaster's (Model 3)
            forecasted monthly growth rate here. If omitted, flat (0%)
            prices are assumed - noted in the result, and likely
            understates the value of storing.

    Returns:
        A dict with `ok: bool`. On success: `recommendation`, `revenue`,
        `storage_cost`, `transport_cost`, `spoilage_loss_value`,
        `net_profit`, `alternatives` (every option considered, for
        transparency), `notes` (assumptions/defaults used).
    """
    return optimize_supply_chain(
        item=item,
        quantity_tonnes=quantity_tonnes,
        current_price_per_quintal=current_price_per_quintal,
        direct_to_market_distance_km=direct_to_market_distance_km,
        price_growth_pct_per_month=price_growth_pct_per_month or 0.0,
    )