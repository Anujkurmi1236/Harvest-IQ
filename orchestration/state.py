from typing import Optional, TypedDict


class HarvestState(TypedDict, total=False):

    item: str
    year: int
    area_harvested: Optional[float]
    quantity_tonnes: float
    current_price_per_quintal: float
    direct_to_market_distance_km: float


    yield_result: dict
    weather_result: dict
    aggregated_context: dict
    price_result: dict
    supply_chain_result: dict

    errors: list[str]