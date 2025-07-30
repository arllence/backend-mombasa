from rest_framework.routers import DefaultRouter
from invoice_tracking import views

router = DefaultRouter(trailing_slash=False)

router.register('psd', views.CoreViewSet, basename='psd')
router.register('psd-reports',views.ReportsViewSet, basename='psd-reports')
router.register('psd-analytics',views.AnalyticsViewSet, basename='psd-analytics')
   
                         
urlpatterns = router.urls