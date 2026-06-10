"""DRF serializers for PricePilot's API."""
from rest_framework import serializers

from .models import PriceRecommendation, Product, SalesRecord


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id", "sku", "name", "category", "base_price", "unit_cost",
            "min_price", "max_price", "inventory", "rating",
        ]


class SalesRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesRecord
        fields = [
            "id", "date", "price", "competitor_price", "site_traffic",
            "units_sold", "converted",
        ]


class PriceRecommendationSerializer(serializers.ModelSerializer):
    product = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = PriceRecommendation
        fields = [
            "id", "product", "recommended_price", "expected_demand",
            "expected_revenue", "expected_profit", "purchase_likelihood",
            "strategy", "created_at",
        ]


class RecommendRequestSerializer(serializers.Serializer):
    """Validates the body of a price-recommendation request."""
    product_id = serializers.IntegerField()
    competitor_price = serializers.FloatField(required=False)
    day_of_week = serializers.IntegerField(required=False, default=2, min_value=0, max_value=6)
    is_weekend = serializers.BooleanField(required=False, default=False)
    is_holiday_season = serializers.BooleanField(required=False, default=False)
    site_traffic = serializers.IntegerField(required=False, default=1200, min_value=0)
    strategy = serializers.ChoiceField(
        choices=["maximize_revenue", "maximize_profit", "balance_revenue_retention"],
        required=False, default="maximize_revenue",
    )
    epsilon = serializers.FloatField(required=False, default=0.0, min_value=0.0, max_value=1.0)
