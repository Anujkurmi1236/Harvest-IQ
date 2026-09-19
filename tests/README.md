# API Tests

Run the API tests from the repository root:

```bash
uv run python -m unittest tests.test_api -v
```

The suite uses FastAPI's `TestClient` and exercises the application in-process. It does not require a server to be running.

Coverage includes:

- `GET /health` returns a healthy status.
- `POST /forecast` runs the full pipeline and returns all result sections.
- `POST /forecast` rejects requests missing required business inputs.
