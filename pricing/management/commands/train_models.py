"""Train the demand regressor and conversion classifier from the DB, then
export a CSV snapshot of the training data for reviewers."""
import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand

from pricing.ml.demand_model import train_models
from pricing.models import SalesRecord


class Command(BaseCommand):
    help = "Train PricePilot's ML models on the historical sales data."

    def handle(self, *args, **opts):
        qs = SalesRecord.objects.select_related("product").all()
        if not qs.exists():
            self.stderr.write("No sales records. Run `generate_data` first.")
            return

        rows = []
        for r in qs.iterator():
            rows.append({
                "sku": r.product.sku,
                "category": r.product.category,
                "base_price": float(r.product.base_price),
                "rating": r.product.rating,
                "inventory": r.product.inventory,
                "price": float(r.price),
                "competitor_price": float(r.competitor_price),
                "day_of_week": r.day_of_week,
                "is_weekend": int(r.is_weekend),
                "is_holiday_season": int(r.is_holiday_season),
                "site_traffic": r.site_traffic,
                "units_sold": r.units_sold,
                "converted": int(r.converted),
            })
        df = pd.DataFrame(rows)

        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(settings.DATA_DIR / "sales_history.csv", index=False)

        self.stdout.write(f"Training on {len(df):,} rows...")
        metrics = train_models(df, settings.ML_MODELS_DIR)

        self.stdout.write(self.style.SUCCESS("Models trained and saved."))
        reg, clf = metrics["regression"], metrics["classification"]
        self.stdout.write(
            f"  Demand regressor   -> R2={reg['r2']}  MAE={reg['mae']} units"
        )
        self.stdout.write(
            f"  Conversion clf     -> Accuracy={clf['accuracy']}  ROC-AUC={clf['roc_auc']}"
        )
