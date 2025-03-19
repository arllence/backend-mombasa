from rest_framework.routers import DefaultRouter
from mhd import views

router = DefaultRouter(trailing_slash=False)

router.register('smr', views.MHSViewSet, basename='smr')
router.register('smr-reports',views.ReportsViewSet, basename='smr-reports')
router.register('smr-analytics',views.AnalyticsViewSet, basename='smr-analytics')
router.register('smr-generics',views.GenericsViewSet, basename='smr-generics')
   
                         
urlpatterns = router.urls