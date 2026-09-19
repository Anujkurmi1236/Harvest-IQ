# Test Results

Command:

```bash
uv run python -m unittest tests.test_api -v
```

Result from 2026-09-19:

```text
Ran 3 tests in 3.028s

OK
```

Passed tests:

- `test_health_endpoint`
- `test_forecast_endpoint_returns_pipeline_results`
- `test_forecast_requires_business_inputs`

The run emitted non-failing deprecation warnings from FastAPI/Starlette's current `TestClient` dependency path and Joblib with NumPy 2.5.
