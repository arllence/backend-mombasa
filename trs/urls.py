from rest_framework.routers import DefaultRouter
from trs import views

router = DefaultRouter(trailing_slash=False)

router.register('trs', views.TrsViewSet, basename='trs')
# router.register('mmqs-reports',views.MMQSReportsViewSet, basename='mmqs-reports')
# router.register('mmqs-analytics',views.MMQSAnalyticsViewSet, basename='mmqs-analytics')
   
                         
urlpatterns = router.urls