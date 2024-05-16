from rest_framework.routers import DefaultRouter
from srrs import views

router = DefaultRouter(trailing_slash=False)

router.register('srrs', views.SrrsViewSet, basename='srrs')
router.register('trs-reports',views.TRSReportsViewSet, basename='trs-reports')
router.register('trs-analytics',views.TRSAnalyticsViewSet, basename='trs-analytics')
   
                         
urlpatterns = router.urls