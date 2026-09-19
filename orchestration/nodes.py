from ml.yield_predictor.src.predict import predict_yield
from ml.weather_analyzer.src.predict import predict_weather
from ml.market_forecaster.src.predict import predict_price
from ml.supply_chain.src.predict import optimize_supply_chain

from .state import HarvestState

def yield_node(state: HarvestState) -> dict:

    result = predict_yield(
        item=state["item"],
        year=state["year"],
    )

    return {
        "yield_result": result
    }

def weather_node(state: HarvestState) -> dict:
    result = predict_weather(year=state["year"])
    return {"weather_result": result}

def aggregator_node(state: HarvestState) -> dict:
    """
    Fan-in point. Only reads state - both yield_result and weather_result
    are guaranteed present here since this node has incoming edges from
    both parallel branches.
    """
    yield_r = state["yield_result"]
    weather_r = state["weather_result"]
 
    context = {
        "item": state["item"],
        "year": state["year"],
        "predicted_yield_kg_ha": yield_r.get("predicted_yield_kg_ha"),
        "yield_confidence_range": [yield_r.get("low_kg_ha"), yield_r.get("high_kg_ha")],
        "yield_ok": yield_r.get("ok", False),
        "predicted_temp_change_degC": weather_r.get("predicted_temp_change_degC"),
        "environmental_stress_index": weather_r.get("environmental_stress_index"),
        "weather_ok": weather_r.get("ok", False),
        "notes": (yield_r.get("notes") or []) + (weather_r.get("notes") or []),
    }
    return {"aggregated_context": context}

def market_node(state: HarvestState) -> dict:
    result = predict_price(item=state["item"], year=state["year"])
    return {"price_result": result}
 
def _monthly_growth_from_price_result(price_result: dict) -> float:
    """
    predict_price returns index LEVELS (this year vs. last known year), not
    a monthly %. Convert: if it's a genuine forecast (not a historical
    lookup), derive the equivalent constant monthly growth rate that
    compounds to the same total change over `steps_ahead` years.
    """
    if not price_result.get("ok") or price_result.get("is_historical", True):
        return 0.0
    steps = price_result.get("steps_ahead") or 0
    last_level = price_result.get("last_known_index_level")
    pred_level = price_result.get("predicted_index_level")
    if not (steps and last_level and pred_level):
        return 0.0
    return ((pred_level / last_level) ** (1 / (steps * 12)) - 1) * 100

# The yield/price models use FAOSTAT crop-production names ("Rice", "Wheat").
# The supply chain model uses Food Balance Sheet names ("Rice and products",
# "Wheat and products") - a different naming convention in the source data,
# not a bug either dataset can fix on its own. This maps the canonical name
# (what the API caller supplies) to the FBS name where it's known; crops
# without an explicit mapping fall through unchanged (supply_chain's own
# fallback-to-average-loss-rate then kicks in, flagged in its own notes).
CANONICAL_TO_FBS_ITEM = {
    "Rice": "Rice and products",
    "Wheat": "Wheat and products",
    "Maize (corn)": "Maize and products",
    "Barley": "Barley and products",
    "Sorghum": "Sorghum and products",
    "Millet": "Millet and products",
    "Cassava, fresh": "Cassava and products",
    "Potatoes": "Potatoes and products",
    "Sweet potatoes": "Sweet potatoes",
    "Sugar cane": "Sugar cane",
}
 
 
def _to_fbs_item_name(item: str) -> str:
    return CANONICAL_TO_FBS_ITEM.get(item, item)
 
 
def supply_chain_node(state: HarvestState) -> dict:
    price_r = state["price_result"]
    growth_pct_per_month = _monthly_growth_from_price_result(price_r)
 
    result = optimize_supply_chain(
        item=_to_fbs_item_name(state["item"]),
        quantity_tonnes=state["quantity_tonnes"],
        current_price_per_quintal=state["current_price_per_quintal"],
        direct_to_market_distance_km=state["direct_to_market_distance_km"],
        price_growth_pct_per_month=growth_pct_per_month,
    )
    return {"supply_chain_result": result}