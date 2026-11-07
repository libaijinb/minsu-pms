from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('settlements', views.SettlementViewSet, basename='settlement')
router.register('payouts', views.PayoutRetryView, basename='payout')

urlpatterns = router.urls
