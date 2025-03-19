from rest_framework.routers import DefaultRouter
from mhd import views

router = DefaultRouter(trailing_slash=False)

router.register('smr', views.MHSViewSet, basename='smr')
router.register('mhd-reports',views.ReportsViewSet, basename='mhd-reports')
router.register('mhd-analytics',views.AnalyticsViewSet, basename='mhd-analytics')
router.register('smr-generics',views.GenericsViewSet, basename='smr-generics')
   
                         
urlpatterns = router.urls