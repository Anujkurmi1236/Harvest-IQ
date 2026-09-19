import unittest

from fastapi.testclient import TestClient

from api.main import app


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_forecast_endpoint_returns_pipeline_results(self):
        response = self.client.post(
            "/forecast",
            json={
                "item": "Rice",
                "year": 2027,
                "quantity_tonnes": 1000.0,
                "current_price_per_quintal": 2500.0,
                "direct_to_market_distance_km": 50.0,
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(
            set(result),
            {"yield", "weather", "aggregated_context", "market", "supply_chain"},
        )
        self.assertTrue(result["yield"]["ok"])
        self.assertTrue(result["weather"]["ok"])
        self.assertTrue(result["market"]["ok"])
        self.assertTrue(result["supply_chain"]["ok"])
        self.assertIsInstance(result["supply_chain"]["recommendation"], str)

    def test_forecast_requires_business_inputs(self):
        response = self.client.post("/forecast", json={"item": "Rice", "year": 2027})

        self.assertEqual(response.status_code, 422)
        self.assertIn("quantity_tonnes", response.text)
        self.assertIn("current_price_per_quintal", response.text)
        self.assertIn("direct_to_market_distance_km", response.text)


if __name__ == "__main__":
    unittest.main()
