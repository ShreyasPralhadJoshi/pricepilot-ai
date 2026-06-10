# PricePilot AI — Dynamic Pricing Engine

An ML-driven dynamic pricing engine for e-commerce platforms. PricePilot forecasts
demand at any candidate price, scores the full price–revenue curve, and recommends
the price that best meets a chosen business objective — maximising revenue, profit,
or a balance of revenue and customer retention.

Built with **Python, Django, Django REST Framework, and scikit-learn**.

---

## What it does

For any product and market context (competitor price, season, weekend, site traffic),
PricePilot:

1. **Forecasts demand** across a sweep of candidate prices using a trained regression model.
2. **Estimates purchase likelihood** at each price using a classification model.
3. **Scores every candidate price** by the selected strategy and returns the optimal price,
   along with expected demand, revenue, profit, and conversion probability.
4. **Serves it over a REST API** and visualises it on an analytics dashboard.

It also supports an **epsilon-greedy exploration policy** — a reinforcement-learning
concept that lets the engine occasionally explore non-optimal prices to keep learning
from live outcomes instead of always exploiting the current best-known price.

---

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │          Analytics Dashboard          │
                    │   (Chart.js · live price simulator)   │
                    └───────────────────┬───────────────────┘
                                        │  HTTP / JSON
                    ┌───────────────────▼───────────────────┐
                    │      Django REST Framework API         │
                    │  /products  /recommend-price           │
                    │  /predict-demand  /metrics  /sales     │
                    └───────────────────┬───────────────────┘
                                        │
                    ┌───────────────────▼───────────────────┐
                    │           Pricing Engine               │
                    │  price sweep → score → recommend       │
                    │  strategies + epsilon-greedy policy    │
                    └───────────────────┬───────────────────┘
                                        │
                ┌───────────────────────┴───────────────────────┐
                │                                                │
     ┌──────────▼───────────┐                      ┌─────────────▼──────────┐
     │  Demand Regressor     │                      │  Conversion Classifier  │
     │  (GradientBoosting)   │                      │  (RandomForest)         │
     │  predicts units sold  │                      │  predicts buy-likelihood│
     └──────────┬───────────┘                      └─────────────┬──────────┘
                └───────────────────┬────────────────────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │   Historical sales (SQLite)    │
                    │   Product · SalesRecord        │
                    └────────────────────────────────┘
```

---

## Machine learning

| Model | Algorithm | Target | Purpose |
|-------|-----------|--------|---------|
| Demand regressor | Gradient Boosting Regressor | `units_sold` | Forecast demand at a given price |
| Conversion classifier | Random Forest Classifier | `converted` | Estimate purchase likelihood |

Both models share one preprocessing pipeline (standard-scaled numerics + one-hot
encoded category) so training and inference features stay identical. Engineered
features include price-to-competitor ratio, discount depth, seasonality, weekend
flags, site traffic, rating, and inventory.

**Reference performance** (synthetic dataset, 5,400 records, 80/20 split):

- Demand regressor — R² ≈ 0.73, MAE ≈ 2.7 units
- Conversion classifier — Accuracy ≈ 0.69, ROC-AUC ≈ 0.64

> The dataset is **synthetically generated** with a realistic price-elasticity demand
> curve plus seasonality, competitor effects, and noise — so the models learn genuine
> economic structure. Regenerate it any time with the management command below.

---

## Pricing strategies

| Strategy | Objective |
|----------|-----------|
| `maximize_revenue` | Highest expected `price × demand` |
| `maximize_profit` | Highest expected `(price − cost) × demand` |
| `balance_revenue_retention` | Revenue weighted by purchase likelihood (avoids over-pricing) |

---

## Setup

```bash
# 1. Clone and enter
git clone https://github.com/<your-username>/pricepilot-ai.git
cd pricepilot-ai

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up the database
python manage.py migrate

# 5. Generate the dataset and train the models
python manage.py generate_data
python manage.py train_models

# 6. Run the server
python manage.py runserver
```

Open **http://127.0.0.1:8000/** for the dashboard, or
**http://127.0.0.1:8000/api/** for the browsable API.

---

## API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/products/` | List catalogue products |
| `GET`  | `/api/sales/?sku=ELEC-1001` | Historical sales records |
| `POST` | `/api/recommend-price/` | Recommend an optimal price |
| `POST` | `/api/predict-demand/` | Full demand/revenue curve across prices |
| `GET`  | `/api/metrics/` | Dashboard business metrics |
| `GET`  | `/api/recommendations/` | Audit log of past recommendations |

### Example — recommend a price

```bash
curl -X POST http://127.0.0.1:8000/api/recommend-price/ \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "strategy": "maximize_revenue", "is_holiday_season": true}'
```

```json
{
  "product": {"id": 1, "sku": "ELEC-1001", "name": "Wireless Noise-Cancelling Headphones"},
  "strategy": "maximize_revenue",
  "recommendation": {
    "price": 4612.5,
    "expected_demand": 9.84,
    "expected_revenue": 45387.0,
    "expected_profit": 19812.0,
    "purchase_likelihood": 0.61
  }
}
```

**Request body fields:** `product_id` (required), `competitor_price`, `day_of_week`,
`is_weekend`, `is_holiday_season`, `site_traffic`, `strategy`, `epsilon` (exploration rate).

---

## Analytics dashboard

The dashboard tracks four business metrics and includes a live price simulator:

1. **Pricing trends** — average recommended price by strategy
2. **Inventory levels** — stock per product
3. **Revenue performance** — units sold by category
4. **Profit margins** — margin percentage per product

---

## Project structure

```
pricepilot-ai/
├── manage.py
├── requirements.txt
├── pricepilot/              # Django project config
│   ├── settings.py
│   └── urls.py
└── pricing/                 # main app
    ├── models.py            # Product, SalesRecord, PriceRecommendation
    ├── serializers.py       # DRF serializers + request validation
    ├── views.py             # API endpoints + dashboard
    ├── urls.py              # API routing
    ├── admin.py
    ├── tests.py
    ├── ml/
    │   ├── features.py      # shared feature engineering
    │   ├── demand_model.py  # train + load the two models
    │   └── pricing_engine.py# price sweep, scoring, epsilon-greedy
    ├── management/commands/
    │   ├── generate_data.py # synthetic e-commerce dataset
    │   └── train_models.py  # train + export CSV snapshot
    └── templates/pricing/
        └── dashboard.html   # Chart.js analytics dashboard
```

---

## Running tests

```bash
python manage.py test pricing
```

---

## Tech stack

Python · Django · Django REST Framework · scikit-learn · pandas · NumPy · Chart.js · SQLite

## License

MIT — see [LICENSE](LICENSE).
