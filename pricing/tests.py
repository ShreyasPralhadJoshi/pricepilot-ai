"""Tests for PricePilot's models, ML engine, and API."""
import pandas as pd
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from pricing.ml.demand_model import DemandPredictor, train_models
from pricing.ml.pricing_engine import PriceContext, PricingEngine
from pricing.models import Product, SalesRecord


def _toy_dataframe(n=400):
    import numpy as np
    rng = np.random.default_rng(0)
    base = 1000
    price = rng.uniform(700, 1250, n)
    units = np.maximum(0, (15000 / price) + rng.normal(0, 1, n)).round()
    return pd.DataFrame({
        "category": rng.choice(["electronics", "fashion"], n),
        "base_price": base, "rating": 4.2, "inventory": 100,
        "price": price, "competitor_price": rng.uniform(800, 1200, n),
        "day_of_week": rng.integers(0, 7, n), "is_weekend": rng.integers(0, 2, n),
        "is_holiday_season": rng.integers(0, 2, n), "site_traffic": rng.integers(800, 2200, n),
        "units_sold": units, "converted": (units >= 12).astype(int),
    })


class MLEngineTests(TestCase):
    def test_train_and_recommend(self):
        import tempfile
        from pathlib import Path
        df = _toy_dataframe()
        with tempfile.TemporaryDirectory() as d:
            metrics = train_models(df, Path(d))
            self.assertIn("regression", metrics)
            predictor = DemandPredictor(Path(d))
            engine = PricingEngine(predictor, n_candidates=20)
            product = {"category": "electronics", "base_price": 1000, "unit_cost": 500,
                       "min_price": 700, "max_price": 1250, "inventory": 100, "rating": 4.2}
            quote = engine.recommend(product, PriceContext(competitor_price=1000))
            self.assertTrue(700 <= quote.price <= 1250)
            self.assertGreaterEqual(quote.expected_demand, 0)


class APITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(
            sku="TEST-1", name="Test", category="electronics",
            base_price=1000, unit_cost=500, min_price=700, max_price=1250,
            inventory=50, rating=4.3,
        )

    def test_products_endpoint(self):
        resp = self.client.get("/api/products/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 1)

    def test_metrics_endpoint(self):
        resp = self.client.get("/api/metrics/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("profit_margins", resp.json())
