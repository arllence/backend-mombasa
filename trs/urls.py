from rest_framework.routers import DefaultRouter
from mms import views

router = DefaultRouter(trailing_slash=False)

router.register('mms',views.MmsViewSet, basename='mms')
router.register('mmqs-reports',views.MMQSReportsViewSet, basename='mmqs-reports')
router.register('mmqs-analytics',views.MMQSAnalyticsViewSet, basename='mmqs-analytics')
   
                         
urlpatterns = router.urls