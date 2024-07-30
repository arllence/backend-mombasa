from rest_framework.routers import DefaultRouter
from ams import views

router = DefaultRouter(trailing_slash=False)

router.register('ams', views.AMSViewSet, basename='ams')
# router.register('asa-reports',views.ReportsViewSet, basename='asa-reports')
# router.register('asa-analytics',views.ASAAnalyticsViewSet, basename='asa-analytics')
   
                         
urlpatterns = router.urls