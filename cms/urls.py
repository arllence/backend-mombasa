from rest_framework.routers import DefaultRouter
from cms import views

router = DefaultRouter(trailing_slash=False)

router.register('cms', views.CoreViewSet, basename='cms')
router.register('cms-reports',views.ReportsViewSet, basename='cms-reports')
router.register('cms-analytics',views.AnalyticsViewSet, basename='cms-analytics')
   
                         
urlpatterns = router.urls