from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('orders', views.OrderViewSet, basename='order')

urlpatterns = [
    path('inspections/', views.InspectionListView.as_view(), name='inspection_list'),
    path('inspections/submit/', views.InspectionSubmitView.as_view(), name='inspection_submit'),
    *router.urls,
]
