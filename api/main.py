from typing import Optional, cast
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from orchestration.graph import compiled_graph
from orchestration.state import HarvestState

app = FastAPI(
    title="Harvest-IQ Orchestration API",
    description="Yield + Weather (parallel) -> Aggregate -> Market Forecaster -> Supply Chain Optimizer",
)

class ForecastRequest(BaseModel):
    item: str = Field(..., examples=["Rice"])
    year: int = Field(..., examples=[2027])
    area_harvested: Optional[float] = Field(
        None, description="Hectares. Defaults to this crop's historical median if omitted."
    )
    quantity_tonnes: float = Field(..., description="Harvest quantity for the supply chain decision.")
    current_price_per_quintal: float = Field(
        ..., description="TODAY's real ₹/quintal market price - required, not derivable from the model data."
    )
    direct_to_market_distance_km: float = Field(..., description="Farm-to-market distance for the sell-now baseline.")


@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/forecast")
def forecast(req: ForecastRequest):
    """
    Runs the full pipeline: yield + weather in parallel, aggregated, then
    fed sequentially into the market forecaster and supply chain optimizer.
    Returns every node's output, not just the final one - so the caller
    (or an LLM summarizing this for a user) can see the full reasoning
    chain, not a black-box final number.
    """
    try:
        final_state = compiled_graph.invoke(cast(HarvestState, req.model_dump()))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
 
    return {
        "yield": final_state.get("yield_result"),
        "weather": final_state.get("weather_result"),
        "aggregated_context": final_state.get("aggregated_context"),
        "market": final_state.get("price_result"),
        "supply_chain": final_state.get("supply_chain_result"),
    }