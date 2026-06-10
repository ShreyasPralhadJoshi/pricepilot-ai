"""API and dashboard views for PricePilot AI."""
from functools import lru_cache

from django.conf import settings
from django.db.models import Avg, Sum
from django.shortcuts import render
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .ml.demand_model import DemandPredictor
from .ml.pricing_engine import PriceContext, PricingEngine, quote_to_dict
from .models import PriceRecommendation, Product, SalesRecord
from .serializers import (
    PriceRecommendationSerializer,
    ProductSerializer,
    RecommendRequestSerializer,
    SalesRecordSerializer,
)


@lru_cache(maxsize=1)
def _engine() -> PricingEngine:
    """Load models once and reuse. Raises a clear error if not trained yet."""
    predictor = DemandPredictor(settings.ML_MODELS_DIR)
    return PricingEngine(predictor)


def _product_dict(p: Product) -> dict:
    return {
        "category": p.category,
        "base_price": float(p.base_price),
        "unit_cost": float(p.unit_cost),
        "min_price": float(p.min_price),
        "max_price": float(p.max_price),
        "inventory": p.inventory,
        "rating": p.rating,
    }


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class SalesRecordViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SalesRecordSerializer

    def get_queryset(self):
        qs = SalesRecord.objects.select_related("product").all()
        sku = self.request.query_params.get("sku")
        if sku:
            qs = qs.filter(product__sku=sku)
        return qs[:500]


@api_view(["POST"])
def recommend_price(request):
    """Recommend an optimal price for a product given market context."""
    req = RecommendRequestSerializer(data=request.data)
    req.is_valid(raise_exception=True)
    data = req.validated_data

    try:
        product = Product.objects.get(pk=data["product_id"])
    except Product.DoesNotExist:
        return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        engine = _engine()
    except FileNotFoundError:
        return Response(
            {"error": "Models not trained. Run `python manage.py train_models`."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    ctx = PriceContext(
        competitor_price=data.get("competitor_price") or float(product.base_price),
        day_of_week=data["day_of_week"],
        is_weekend=data["is_weekend"],
        is_holiday_season=data["is_holiday_season"],
        site_traffic=data["site_traffic"],
    )
    quote = engine.recommend(
        _product_dict(product), ctx,
        strategy=data["strategy"], epsilon=data["epsilon"],
    )

    rec = PriceRecommendation.objects.create(
        product=product,
        recommended_price=quote.price,
        expected_demand=quote.expected_demand,
        expected_revenue=quote.expected_revenue,
        expected_profit=quote.expected_profit,
        purchase_likelihood=quote.purchase_likelihood,
        strategy=data["strategy"],
    )

    return Response({
        "product": {"id": product.id, "sku": product.sku, "name": product.name},
        "strategy": data["strategy"],
        "recommendation": quote_to_dict(quote),
        "recommendation_id": rec.id,
    })


@api_view(["POST"])
def predict_demand(request):
    """Return the full predicted demand/revenue curve across the price range."""
    pid = request.data.get("product_id")
    try:
        product = Product.objects.get(pk=pid)
    except (Product.DoesNotExist, ValueError, TypeError):
        return Response({"error": "Valid product_id required."},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        engine = _engine()
    except FileNotFoundError:
        return Response({"error": "Models not trained."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    ctx = PriceContext(
        competitor_price=float(request.data.get("competitor_price") or product.base_price),
        is_holiday_season=bool(request.data.get("is_holiday_season", False)),
    )
    curve = [quote_to_dict(q) for q in engine.quote_curve(_product_dict(product), ctx)]
    return Response({"product": product.sku, "curve": curve})


@api_view(["GET"])
def metrics(request):
    """The four business metrics surfaced on the analytics dashboard."""
    products = Product.objects.all()

    # 1. Pricing trends: avg recommended price per strategy (latest 200)
    recent = PriceRecommendation.objects.all()[:200]
    pricing_trends = list(
        PriceRecommendation.objects.values("strategy")
        .annotate(avg_price=Avg("recommended_price"),
                  avg_revenue=Avg("expected_revenue"))
    )

    # 2. Inventory levels
    inventory = [
        {"sku": p.sku, "name": p.name, "inventory": p.inventory}
        for p in products
    ]

    # 3. Revenue performance (historical, from sales)
    revenue_by_cat = list(
        SalesRecord.objects.values("product__category")
        .annotate(units=Sum("units_sold"))
        .order_by("-units")
    )

    # 4. Profit margins per product
    margins = []
    for p in products:
        base = float(p.base_price) or 1.0
        margin = (base - float(p.unit_cost)) / base * 100
        margins.append({"sku": p.sku, "name": p.name, "margin_pct": round(margin, 1)})

    return Response({
        "pricing_trends": pricing_trends,
        "inventory_levels": inventory,
        "revenue_performance": revenue_by_cat,
        "profit_margins": margins,
        "total_recommendations": PriceRecommendation.objects.count(),
    })


def dashboard(request):
    """Serve the analytics dashboard HTML."""
    return render(request, "pricing/dashboard.html", {
        "products": Product.objects.all(),
    })


class RecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PriceRecommendation.objects.select_related("product").all()
    serializer_class = PriceRecommendationSerializer
