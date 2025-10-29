from rest_framework.routers import DefaultRouter
from expenditure import views

router = DefaultRouter(trailing_slash=False)

router.register('expenditure', views.CoreViewSet, basename='expenditure')
# router.register('cms-reports',views.ReportsViewSet, basename='cms-reports')
# router.register('cms-analytics',views.AnalyticsViewSet, basename='cms-analytics')
   
                         
urlpatterns = router.urls