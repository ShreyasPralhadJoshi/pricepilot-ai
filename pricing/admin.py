from django.contrib import admin

from .models import PriceRecommendation, Product, SalesRecord


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "base_price", "inventory", "rating")
    list_filter = ("category",)
    search_fields = ("sku", "name")


@admin.register(SalesRecord)
class SalesRecordAdmin(admin.ModelAdmin):
    list_display = ("product", "date", "price", "units_sold", "converted")
    list_filter = ("is_holiday_season", "is_weekend")


@admin.register(PriceRecommendation)
class PriceRecommendationAdmin(admin.ModelAdmin):
    list_display = ("product", "recommended_price", "expected_revenue", "strategy", "created_at")
    list_filter = ("strategy",)
