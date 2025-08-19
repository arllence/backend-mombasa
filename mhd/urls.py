from rest_framework.routers import DefaultRouter
from mhd import views

router = DefaultRouter(trailing_slash=False)

router.register('mhd', views.MHSViewSet, basename='mhd')
router.register('job-cards', views.JobCardViewSet, basename='job-cards')
router.register('mhd-reports',views.ReportsViewSet, basename='mhd-reports')
router.register('mhd-analytics',views.AnalyticsViewSet, basename='mhd-analytics')
router.register('mhd-generics',views.GenericsViewSet, basename='mhd-generics')
   
                         
urlpatterns = router.urls