from rest_framework.routers import DefaultRouter
from dbmanager import views

router = DefaultRouter(trailing_slash=False)

router.register('db-manager', views.DbManagerViewSet, basename='db-manager')
# router.register('s3-reports',views.ReportsViewSet, basename='s3-reports')
# router.register('s3-analytics',views.AnalyticsViewSet, basename='s3-analytics')
   
                         
urlpatterns = router.urls