import sys
import unittest
from pathlib import Path

# Bootstrap project root and backend dir into sys.path
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = Path(__file__).resolve().parent
for _p in (str(_ROOT), str(_BACKEND)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi.testclient import TestClient

try:
    from backend import app as api
except ImportError:
    import app as api


class ValuationAPITests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client_context = TestClient(api.app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")
        self.assertIn("v1", response.json()["models_loaded"])

    def test_cities(self):
        response = self.client.get("/api/v1/cities")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Gurgaon", response.json()["cities"])

    def test_locality_search(self):
        response = self.client.get(
            "/api/v1/localities",
            params={"city": "Gurgaon", "q": "Sector 63"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            any("Sector 63" in name for name in response.json()["localities"])
        )

    def test_valid_valuation_v1(self):
        response = self.client.post(
            "/api/v1/valuate",
            json={
                "city": "Gurgaon",
                "locality": "Sector 63",
                "sqft": 3794,
                "bhk": 5,
                "floor": 2,
                "age_years": 0.5,
                "model_version": "v1"
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        required_fields = [
            "model_version", "currency", "unit",
            "price_lakhs", "range_low_lakhs", "range_high_lakhs",
            "nominal_interval_coverage", "auto_accept", "review_reason",
            "locality_sample_count", "location_source",
            "infrastructure_source", "comparables"
        ]

        for field in required_fields:
            self.assertIn(field, data)

        self.assertEqual(data["currency"], "INR")
        self.assertEqual(data["unit"], "lakh")
        self.assertAlmostEqual(data["price_lakhs"], 580.17, places=2)
        self.assertLessEqual(len(data["comparables"]), 3)

        if data["comparables"]:
            self.assertIn("row_id", data["comparables"][0])
            self.assertIn("distance_km", data["comparables"][0])

    def test_valid_valuation_v2(self):
        if "v2" not in api.bundles:
            self.skipTest("V2 model bundle is unavailable")

        response = self.client.post(
            "/api/v1/valuate",
            json={
                "city": "Gurgaon",
                "locality": "Sector 63",
                "sqft": 3794,
                "bhk": 5,
                "model_version": "v2"
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("ps1-v2", response.json()["model_version"])

    def test_invalid_area(self):
        response = self.client.post(
            "/api/v1/valuate",
            json={
                "city": "Gurgaon",
                "locality": "Sector 63",
                "sqft": 100,
                "bhk": 2
            }
        )
        self.assertEqual(response.status_code, 422)

    def test_unsupported_city(self):
        response = self.client.post(
            "/api/v1/valuate",
            json={
                "city": "Unknown City",
                "locality": "Unknown Locality",
                "sqft": 1000,
                "bhk": 2
            }
        )
        self.assertEqual(response.status_code, 422)

    def test_coordinate_pair_required(self):
        payload = {
            "city": "Gurgaon",
            "locality": "Sector 63",
            "sqft": 1000,
            "bhk": 2,
            "lat": 28.4
        }
        response = self.client.post("/api/v1/valuate", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_unknown_fields_rejected(self):
        response = self.client.post(
            "/api/v1/valuate",
            json={
                "city": "Gurgaon",
                "locality": "Sector 63",
                "sqft": 1000,
                "bhk": 2,
                "unknown_field": "not allowed"
            }
        )
        self.assertEqual(response.status_code, 422)

    def test_model_unavailable_returns_503(self):
        original_bundles = api.bundles.copy()

        try:
            api.bundles.clear()

            health_response = self.client.get("/health")
            self.assertEqual(health_response.status_code, 503)

            valuation_response = self.client.post(
                "/api/v1/valuate",
                json={
                    "city": "Gurgaon",
                    "locality": "Sector 63",
                    "sqft": 1000,
                    "bhk": 2
                }
            )
            self.assertEqual(valuation_response.status_code, 503)

        finally:
            api.bundles.update(original_bundles)
    def test_non_finite_area_rejected(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value):
                response = self.client.post(
                    "/api/v1/valuate",
                    json={
                        "city": "Gurgaon",
                        "locality": "Sector 63",
                        "sqft": value,
                        "bhk": 2
                    }
                )
                self.assertEqual(response.status_code, 422)
    def test_invalid_indian_coordinates_rejected(self):
        invalid_coordinates = [
            (7.0, 77.0),
            (36.0, 77.0),
            (28.0, 67.0),
            (28.0, 98.0)
        ]

        for lat, lon in invalid_coordinates:
            with self.subTest(lat=lat, lon=lon):
                response = self.client.post(
                    "/api/v1/valuate",
                    json={
                        "city": "Gurgaon",
                        "locality": "Sector 63",
                        "sqft": 1000,
                        "bhk": 2,
                        "lat": lat,
                        "lon": lon
                    }
                )
                self.assertEqual(response.status_code, 422)
    def test_unknown_locality_with_coordinates_requires_review(self):
        response = self.client.post(
            "/api/v1/valuate",
            json={
                "city": "Gurgaon",
                "locality": "Definitely Unknown Locality",
                "sqft": 1000,
                "bhk": 2,
                "lat": 28.4,
                "lon": 77.1
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["auto_accept"])
        self.assertIsNotNone(data["review_reason"])
if __name__ == "__main__":
    unittest.main()
