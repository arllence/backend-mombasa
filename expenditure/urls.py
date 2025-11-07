from rest_framework.routers import DefaultRouter
from expenditure import views

router = DefaultRouter(trailing_slash=False)

router.register('expenditure', views.CoreViewSet, basename='expenditure')
router.register('expenditure-reports',views.ReportsViewSet, basename='expenditure-reports')
router.register('expenditure-analytics',views.AnalyticsViewSet, basename='expenditure-analytics')
   
                         
urlpatterns = router.urls