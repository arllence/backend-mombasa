from rest_framework.routers import DefaultRouter
from sls import views

router = DefaultRouter(trailing_slash=False)

router.register('s3', views.S3ViewSet, basename='s3')
router.register('s3-reports',views.ReportsViewSet, basename='s3-reports')
router.register('s3-analytics',views.AnalyticsViewSet, basename='s3-analytics')
   
                         
urlpatterns = router.urls