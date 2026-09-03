from langchain_core.tools import tool
from predict import predict_weather
 
 
@tool
def predict_weather_tool(year: int) -> dict:
    """
    Get predicted temperature change and an environmental stress index for
    India for a given year. Runs in parallel with the yield model - both
    feed the same year's context into a downstream aggregator, which then
    feeds the market price forecaster and supply chain optimizer.
 
    Use this when the user asks about temperature trends, climate/weather
    context, or environmental conditions for a year. Do NOT use it for
    crop yield, rainfall/humidity (not available in the underlying data),
    or price/supply questions - those belong to the other models.
 
    Args:
        year: Year to get the prediction for, e.g. 2025. Years outside
            1961-2025 are extrapolated from a linear trend, noted in the
            result. The environmental stress index draws on land-use/
            land-cover/emissions data that doesn't cover every year - gaps
            are filled from the nearest available year, also noted.
 
    Returns:
        A dict with `ok: bool`. On success: `predicted_temp_change_degC`,
        `typical_error_degC`, `environmental_stress_index` (0-100, higher =
        more stress - a documented rule-based score, not a trained
        prediction), `stress_components` (the four sub-scores behind it),
        and `notes` (any fallback years or extrapolation caveats applied).
        On failure: `error`.
    """
    return predict_weather(year=year)