from rest_framework.routers import DefaultRouter
from cms import views

router = DefaultRouter(trailing_slash=False)

router.register('core', views.CoreViewSet, basename='core')
# router.register('s3-reports',views.ReportsViewSet, basename='s3-reports')
# router.register('s3-analytics',views.AnalyticsViewSet, basename='s3-analytics')
   
                         
urlpatterns = router.urls