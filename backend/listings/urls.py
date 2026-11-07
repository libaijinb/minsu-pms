from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('listings', views.ListingViewSet, basename='listing')
router.register('price-rules', views.PriceRuleViewSet, basename='price_rule')

urlpatterns = router.urls
