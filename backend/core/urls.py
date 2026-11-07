from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('reviews', views.ReviewViewSet, basename='review')
router.register('notifications', views.NotificationViewSet, basename='notification')

urlpatterns = [
    path('stats/overview/', views.StatsView.as_view(), name='stats_overview'),  # 经营统计：OCC/ADR/RevPAR
    *router.urls,
]
