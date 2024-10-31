from rest_framework.routers import DefaultRouter
from dbmanager import views

router = DefaultRouter(trailing_slash=False)

router.register('db-manager', views.DbManagerViewSet, basename='db-manager')
# router.register('db-manager-reports',views.ReportsViewSet, basename='db-manager-reports')
router.register('db-manager-analytics',views.AnalyticsViewSet, basename='db-manager-analytics')
   
                         
urlpatterns = router.urls