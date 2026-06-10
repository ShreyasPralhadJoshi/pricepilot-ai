"""Database models for PricePilot AI."""
from django.db import models


class Product(models.Model):
    """A catalogue product whose price PricePilot optimises."""

    CATEGORY_CHOICES = [
        ("electronics", "Electronics"),
        ("fashion", "Fashion"),
        ("home", "Home & Kitchen"),
        ("beauty", "Beauty"),
        ("sports", "Sports & Fitness"),
    ]

    sku = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    min_price = models.DecimalField(max_digits=10, decimal_places=2)
    max_price = models.DecimalField(max_digits=10, decimal_places=2)
    inventory = models.IntegerField(default=0)
    rating = models.FloatField(default=4.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sku"]

    def __str__(self):
        return f"{self.sku} – {self.name}"


class SalesRecord(models.Model):
    """A historical observation: a product offered at a price and the demand seen."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="sales_records"
    )
    date = models.DateField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    competitor_price = models.DecimalField(max_digits=10, decimal_places=2)
    day_of_week = models.IntegerField()  # 0 = Monday
    is_weekend = models.BooleanField(default=False)
    is_holiday_season = models.BooleanField(default=False)
    site_traffic = models.IntegerField(default=0)
    units_sold = models.IntegerField(default=0)
    converted = models.BooleanField(default=False)  # high-conversion flag

    class Meta:
        ordering = ["-date"]
        indexes = [models.Index(fields=["product", "date"])]

    def __str__(self):
        return f"{self.product.sku} @ {self.price} -> {self.units_sold} units"


class PriceRecommendation(models.Model):
    """An audit log of recommendations the engine has served."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="recommendations"
    )
    recommended_price = models.DecimalField(max_digits=10, decimal_places=2)
    expected_demand = models.FloatField()
    expected_revenue = models.FloatField()
    expected_profit = models.FloatField()
    purchase_likelihood = models.FloatField()
    strategy = models.CharField(max_length=32, default="maximize_revenue")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.sku} -> {self.recommended_price} ({self.strategy})"
