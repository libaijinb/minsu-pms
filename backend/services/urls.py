from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('cleaning-tasks', views.CleaningTaskViewSet, basename='cleaning_task')
router.register('repair-tickets', views.RepairTicketViewSet, basename='repair_ticket')

urlpatterns = router.urls
