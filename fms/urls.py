from rest_framework.routers import DefaultRouter
from fms import views

router = DefaultRouter(trailing_slash=False)

router.register('fms', views.FmsViewSet, basename='fms')
router.register('fms-reports',views.ReportsViewSet, basename='fms-reports')
router.register('fms-analytics',views.AnalyticsViewSet, basename='fms-analytics')
router.register('fms-generics',views.GenericsViewSet, basename='fms-generics')
   
                         
urlpatterns = router.urls