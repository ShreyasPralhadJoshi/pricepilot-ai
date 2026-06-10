"""Generate a realistic synthetic e-commerce sales dataset.

Demand is simulated with a downward-sloping price-elasticity curve plus
seasonality, weekend uplift, competitor-price effects and noise — so the
trained models learn genuine economic structure rather than memorising noise.
"""
import random
from datetime import date, timedelta

import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand

from pricing.models import Product, SalesRecord

CATALOGUE = [
    # sku, name, category, base, cost, rating, elasticity
    ("ELEC-1001", "Wireless Noise-Cancelling Headphones", "electronics", 4999, 2600, 4.5, 1.8),
    ("ELEC-1002", "Smart Fitness Band", "electronics", 2499, 1100, 4.2, 2.2),
    ("ELEC-1003", "1080p Webcam", "electronics", 1799, 800, 4.0, 2.0),
    ("FASH-2001", "Running Shoes", "fashion", 2999, 1300, 4.3, 1.6),
    ("FASH-2002", "Cotton Casual Shirt", "fashion", 1299, 500, 4.1, 1.9),
    ("HOME-3001", "Stainless Steel Cookware Set", "home", 3499, 1700, 4.4, 1.4),
    ("HOME-3002", "Air Fryer 4L", "home", 5499, 3000, 4.6, 1.5),
    ("BEAU-4001", "Vitamin C Face Serum", "beauty", 899, 300, 4.2, 2.4),
    ("SPRT-5001", "Adjustable Dumbbell 20kg", "sports", 4299, 2200, 4.5, 1.3),
    ("SPRT-5002", "Yoga Mat Premium", "sports", 999, 380, 4.1, 2.1),
]


class Command(BaseCommand):
    help = "Generate synthetic products and historical sales records."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=540,
                            help="Days of history per product (default 540).")
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **opts):
        random.seed(opts["seed"])
        np.random.seed(opts["seed"])

        self.stdout.write("Clearing existing data...")
        SalesRecord.objects.all().delete()
        Product.objects.all().delete()

        start = date.today() - timedelta(days=opts["days"])
        records = []

        for sku, name, cat, base, cost, rating, elasticity in CATALOGUE:
            product = Product.objects.create(
                sku=sku, name=name, category=cat,
                base_price=base, unit_cost=cost,
                min_price=round(base * 0.7, 2), max_price=round(base * 1.25, 2),
                inventory=random.randint(40, 400), rating=rating,
            )

            for d in range(opts["days"]):
                day = start + timedelta(days=d)
                dow = day.weekday()
                is_weekend = dow >= 5
                # Oct-Dec festive season in India (Diwali/year-end sales)
                is_holiday = day.month in (10, 11, 12)

                # Offered price wanders around base price
                price = base * np.random.uniform(0.72, 1.22)
                competitor = base * np.random.uniform(0.85, 1.15)
                traffic = int(np.random.normal(1500, 400))
                traffic = max(200, traffic)

                # --- demand model (ground truth for the simulation) ---
                price_effect = (base / price) ** elasticity
                comp_effect = (competitor / price) ** 0.6
                season = 1.35 if is_holiday else 1.0
                weekend = 1.18 if is_weekend else 1.0
                traffic_effect = traffic / 1500.0
                rating_effect = rating / 4.0

                expected = (
                    8 * price_effect * comp_effect * season
                    * weekend * traffic_effect * rating_effect
                )
                units = max(0, int(np.random.poisson(max(0.1, expected))))

                # Conversion: a learnable signal driven by observable features —
                # discount depth, price vs competitor, season, weekend, traffic,
                # rating. Modelled as a logistic probability then sampled, so the
                # classifier can recover real structure (not latent noise).
                discount = (base - price) / base          # higher = cheaper
                comp_ratio = competitor / price            # >1 = we're cheaper
                score = (
                    -1.4
                    + 3.2 * discount
                    + 1.1 * (comp_ratio - 1.0)
                    + 0.55 * is_holiday
                    + 0.30 * is_weekend
                    + 0.45 * (traffic / 1500.0 - 1.0)
                    + 0.40 * (rating - 4.0)
                )
                prob = 1.0 / (1.0 + np.exp(-score))
                converted = bool(np.random.random() < prob)

                records.append(SalesRecord(
                    product=product, date=day,
                    price=round(price, 2), competitor_price=round(competitor, 2),
                    day_of_week=dow, is_weekend=is_weekend,
                    is_holiday_season=is_holiday, site_traffic=traffic,
                    units_sold=units, converted=converted,
                ))

        SalesRecord.objects.bulk_create(records, batch_size=2000)
        self.stdout.write(self.style.SUCCESS(
            f"Created {Product.objects.count()} products and "
            f"{SalesRecord.objects.count()} sales records."
        ))
