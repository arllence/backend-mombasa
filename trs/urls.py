from rest_framework.routers import DefaultRouter
from trs import views

router = DefaultRouter(trailing_slash=False)

router.register('trs', views.TrsViewSet, basename='trs')
# router.register('mmqs-reports',views.MMQSReportsViewSet, basename='mmqs-reports')
router.register('trs-analytics',views.TRSAnalyticsViewSet, basename='trs-analytics')
   
                         
urlpatterns = router.urls