from typing import Optional, TypedDict, Any, Required, NotRequired


class HarvestState(TypedDict, total=False):

    item: Required[str]
    year: Required[int]

    aera_harvested: Optional[float]
    quantity_tonnes: Required[float]
    current_price_per_quintal: Required[float]
    direct_to_market_distance_km: Required[float]

    yield_prediction: NotRequired[dict]
    weather_analysis: NotRequired[dict]
    aggregated_context: NotRequired[dict]
    market_forecast: NotRequired[dict]
    supply_plan: NotRequired[dict]

    errors: list[str]