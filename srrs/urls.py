from rest_framework.routers import DefaultRouter
from srrs import views

router = DefaultRouter(trailing_slash=False)

router.register('srrs', views.SrrsViewSet, basename='srrs')
router.register('srrs-reports',views.SRRSReportsViewSet, basename='srrs-reports')
router.register('srrs-analytics',views.SRRSAnalyticsViewSet, basename='srrs-analytics')
   
                         
urlpatterns = router.urls