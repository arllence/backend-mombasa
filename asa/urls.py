from rest_framework.routers import DefaultRouter
from asa import views

router = DefaultRouter(trailing_slash=False)

router.register('asa', views.ASAViewSet, basename='asa')
# router.register('locums', views.LocumViewSet, basename='locums')
router.register('asa-reports',views.ReportsViewSet, basename='asa-reports')
# router.register('srrs-analytics',views.SRRSAnalyticsViewSet, basename='srrs-analytics')
   
                         
urlpatterns = router.urls