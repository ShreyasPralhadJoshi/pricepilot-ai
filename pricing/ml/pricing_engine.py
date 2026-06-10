"""The dynamic pricing engine.

Given a product and a market context, the engine sweeps candidate prices
between the product's min and max price, asks the demand model how many units
each price would sell, and scores each candidate by the chosen objective
(revenue, profit, or a balance of revenue + retention).

It also supports an epsilon-greedy exploration policy — the "reinforcement
learning concept" used to keep learning from live pricing decisions instead of
always exploiting the current best-known price.
"""
import random
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from .demand_model import DemandPredictor


@dataclass
class PriceContext:
    """Everything the engine needs about the current market moment."""
    competitor_price: float
    day_of_week: int = 2
    is_weekend: bool = False
    is_holiday_season: bool = False
    site_traffic: int = 1200


@dataclass
class PriceQuote:
    price: float
    expected_demand: float
    expected_revenue: float
    expected_profit: float
    purchase_likelihood: float


class PricingEngine:
    STRATEGIES = ("maximize_revenue", "maximize_profit", "balance_revenue_retention")

    def __init__(self, predictor: DemandPredictor, n_candidates: int = 40):
        self.predictor = predictor
        self.n_candidates = n_candidates

    def _candidate_rows(self, product: dict, ctx: PriceContext, prices):
        rows = []
        for p in prices:
            rows.append(
                {
                    "price": p,
                    "competitor_price": ctx.competitor_price,
                    "base_price": product["base_price"],
                    "day_of_week": ctx.day_of_week,
                    "site_traffic": ctx.site_traffic,
                    "rating": product["rating"],
                    "inventory": product["inventory"],
                    "is_weekend": int(ctx.is_weekend),
                    "is_holiday_season": int(ctx.is_holiday_season),
                    "category": product["category"],
                }
            )
        return pd.DataFrame(rows)

    def quote_curve(self, product: dict, ctx: PriceContext) -> list:
        """Return a PriceQuote for every candidate price (the demand curve)."""
        prices = np.linspace(
            float(product["min_price"]), float(product["max_price"]), self.n_candidates
        )
        rows = self._candidate_rows(product, ctx, prices)
        demand = self.predictor.predict_demand(rows)
        conv = self.predictor.predict_conversion(rows)
        cost = float(product["unit_cost"])

        quotes = []
        for price, d, c in zip(prices, demand, conv):
            revenue = price * d
            profit = (price - cost) * d
            quotes.append(
                PriceQuote(
                    price=round(float(price), 2),
                    expected_demand=round(float(d), 2),
                    expected_revenue=round(float(revenue), 2),
                    expected_profit=round(float(profit), 2),
                    purchase_likelihood=round(float(c), 4),
                )
            )
        return quotes

    def _score(self, q: PriceQuote, strategy: str) -> float:
        if strategy == "maximize_profit":
            return q.expected_profit
        if strategy == "balance_revenue_retention":
            # Reward revenue but penalise pushing price far above conversion comfort.
            return q.expected_revenue * (0.5 + 0.5 * q.purchase_likelihood)
        return q.expected_revenue  # default: maximize_revenue

    def recommend(
        self,
        product: dict,
        ctx: PriceContext,
        strategy: str = "maximize_revenue",
        epsilon: float = 0.0,
    ) -> PriceQuote:
        """Recommend a price.

        With probability ``epsilon`` the engine *explores* (returns a random
        candidate) instead of *exploiting* the best-scoring candidate. This is
        the epsilon-greedy bandit policy that lets pricing keep learning online.
        """
        if strategy not in self.STRATEGIES:
            raise ValueError(f"Unknown strategy: {strategy}")

        quotes = self.quote_curve(product, ctx)

        if epsilon > 0 and random.random() < epsilon:
            return random.choice(quotes)  # explore

        return max(quotes, key=lambda q: self._score(q, strategy))  # exploit


def quote_to_dict(q: PriceQuote) -> dict:
    return asdict(q)
