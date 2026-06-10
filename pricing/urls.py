"""URL routing for the pricing app's REST API."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"products", views.ProductViewSet, basename="product")
router.register(r"sales", views.SalesRecordViewSet, basename="sales")
router.register(r"recommendations", views.RecommendationViewSet, basename="recommendation")

urlpatterns = [
    path("", include(router.urls)),
    path("recommend-price/", views.recommend_price, name="recommend-price"),
    path("predict-demand/", views.predict_demand, name="predict-demand"),
    path("metrics/", views.metrics, name="metrics"),
]
