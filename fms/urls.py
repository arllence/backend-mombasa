from rest_framework.routers import DefaultRouter
from fms import views

router = DefaultRouter(trailing_slash=False)

router.register('fms', views.FmsViewSet, basename='fms')
# router.register('locums', views.LocumViewSet, basename='locums')
# router.register('fms-reports',views.SRRSReportsViewSet, basename='fms-reports')
# router.register('fms-analytics',views.SRRSAnalyticsViewSet, basename='fms-analytics')
   
                         
urlpatterns = router.urls