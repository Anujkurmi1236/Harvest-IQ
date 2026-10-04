# Harvest-IQ

Harvest-IQ is an agricultural decision-support platform for India. It combines crop-yield prediction, environmental stress analysis, relative market-price forecasting, and supply-chain optimization in one workflow.

The application exposes the workflow through a FastAPI service and provides a Streamlit dashboard for interactive analysis.

## Features

- Predicts crop yield for a selected crop and year.
- Estimates temperature change and an environmental stress index.
- Forecasts a FAOSTAT price-index level when the requested year is in the future, or returns the historical index level when available.
- Compares sell-now and storage alternatives using quantity, current price, distance, storage costs, and estimated crop loss rates.
- Returns stage-level results, assumptions, fallbacks, and errors instead of hiding them behind a single score.

## How It Works

The LangGraph workflow runs yield and weather analysis in parallel, combines their results, and then runs market forecasting followed by supply-chain optimization:

```text
START
	|-- Yield prediction --|
	|-- Weather analysis --|--> Aggregation --> Market forecast --> Supply-chain optimizer --> END
```

## Requirements

- Python 3.13 or newer
- `uv` for dependency management and command execution

Install `uv` from the [official installation guide](https://docs.astral.sh/uv/getting-started/installation/) if it is not already available.

## Quick Start

From the repository root:

```bash
uv sync
```

Open two terminals from the repository root. In terminal 1, start the API:

```bash
uv run python run_api.py
```

The API is available at `http://127.0.0.1:8000`. Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

The launcher also accepts a custom host or port:

```bash
uv run python run_api.py --host 0.0.0.0 --port 8080
```

Use `--reload` during development. The same values can be configured with the `HOST` and `PORT` environment variables.

In terminal 2, start the Streamlit dashboard:

```bash
uv run streamlit run dashboard/app.py
```

Open the URL printed by Streamlit, leave the API base URL as `http://127.0.0.1:8000`, enter the harvest details, and select **Run Analysis**.

### Hosted deployment

The deployed Streamlit dashboard is available at:

<https://harvest-iq-jblar2crj4dzand5yqeuey.streamlit.app/>

The deployed FastAPI service is available at:

<https://harvest-iq-1d53.onrender.com>

To connect the hosted dashboard to the API:

1. Open the [Harvest-IQ Streamlit dashboard](https://harvest-iq-jblar2crj4dzand5yqeuey.streamlit.app/).
2. In the sidebar, set **API base URL** to `https://harvest-iq-1d53.onrender.com`.
3. Enter the harvest details and select **Run analysis**.

Do not add a trailing slash to the API base URL.

## API

### Health check

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

### Run a forecast

```bash
curl -X POST http://127.0.0.1:8000/forecast \
	-H 'Content-Type: application/json' \
	-d '{
		"item": "Rice",
		"year": 2027,
		"quantity_tonnes": 1000,
		"current_price_per_quintal": 2500,
		"direct_to_market_distance_km": 50
	}'
```

Required fields:

| Field | Type | Description |
| --- | --- | --- |
| `item` | string | Crop name, for example `Rice` or `Wheat` |
| `year` | integer | Target year for the analysis |
| `quantity_tonnes` | number | Quantity available for the supply-chain decision |
| `current_price_per_quintal` | number | Current real-world price in INR per quintal |
| `direct_to_market_distance_km` | number | Farm-to-market distance for the sell-now baseline |

`area_harvested` is optional. When omitted, the yield model uses the crop's historical median area.

The response contains `yield`, `weather`, `aggregated_context`, `market`, and `supply_chain` sections. The market model produces a relative price index, not a currency price. The current market price must be supplied by the caller and is not inferred from the model data.

## Testing

Run the API tests from the repository root:

```bash
uv run python -m unittest tests.test_api -v
```

The tests use FastAPI's in-process `TestClient`; a running API server is not required.

## Repository Layout

```text
api/                  FastAPI application and request models
dashboard/            Streamlit user interface
ml/yield_predictor/   Yield model, artifacts, and prediction code
ml/weather_analyzer/  Weather and environmental stress model
ml/market_forecaster/ Market-index forecasting model
ml/supply_chain/      Storage, transport, loss, and profit optimization
orchestration/        LangGraph state, nodes, and workflow definition
tests/                API tests and test notes
```

The checked-in model artifacts under each `ml/*/output` directory are used at runtime. The source data used to build those artifacts is stored under the corresponding `ml/*/data` directory.

## Notes and Limitations

- Forecasts are model outputs and should be reviewed alongside current local market and farm conditions.
- The market result is an index with base period 2014-2016 = 100; it is not a rupee-denominated forecast.
- Crop names come from the source datasets. The dashboard provides a canonical list and maps supported names to the supply-chain dataset's naming convention.
- Some stages may use documented fallback values when a crop or input is not represented sufficiently in the source data. These notes are returned in the API response and displayed in the dashboard.

