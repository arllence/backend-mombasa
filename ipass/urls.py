from rest_framework.routers import DefaultRouter
from ipass import views

router = DefaultRouter(trailing_slash=False)

router.register('ipass', views.IpassViewSet, basename='ipass')
router.register('ipass-reports',views.ReportsViewSet, basename='ipass-reports')
# router.register('trs-analytics',views.TRSAnalyticsViewSet, basename='trs-analytics')
   
                         
urlpatterns = router.urls