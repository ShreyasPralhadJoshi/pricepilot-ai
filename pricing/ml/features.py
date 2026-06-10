"""Feature engineering shared by training and inference.

Keeping feature construction in one place guarantees that the columns the
models were trained on are exactly the columns we build at prediction time.
"""
import pandas as pd

# Order matters: models are trained on this column order.
NUMERIC_FEATURES = [
    "price",
    "competitor_price",
    "price_ratio",        # price / competitor_price
    "discount_pct",       # (base_price - price) / base_price
    "day_of_week",
    "site_traffic",
    "rating",
    "inventory",
]
BINARY_FEATURES = ["is_weekend", "is_holiday_season"]
CATEGORICAL_FEATURES = ["category"]

ALL_INPUT_FEATURES = NUMERIC_FEATURES + BINARY_FEATURES + CATEGORICAL_FEATURES


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive engineered columns from raw observation columns.

    Expects: price, competitor_price, base_price, day_of_week, site_traffic,
    rating, inventory, is_weekend, is_holiday_season, category.
    """
    df = df.copy()
    df["price_ratio"] = df["price"] / df["competitor_price"].replace(0, 1e-6)
    df["discount_pct"] = (df["base_price"] - df["price"]) / df["base_price"].replace(0, 1e-6)
    return df[ALL_INPUT_FEATURES]
