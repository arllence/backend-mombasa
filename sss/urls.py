from rest_framework.routers import DefaultRouter
from sss import views

router = DefaultRouter(trailing_slash=False)

router.register('sss', views.SSSViewSet, basename='sss')
router.register('sss-reports',views.ReportsViewSet, basename='sss-reports')
router.register('sss-analytics',views.ASAAnalyticsViewSet, basename='sss-analytics')
   
                         
urlpatterns = router.urls