from rest_framework.routers import DefaultRouter
from ctp import views

router = DefaultRouter(trailing_slash=False)

router.register('trainings', views.CoreViewSet, basename='trainings')
router.register('trainings-reports',views.ReportsViewSet, basename='trainings-reports')
router.register('trainings-analytics',views.AnalyticsViewSet, basename='trainings-analytics')
   
                         
urlpatterns = router.urls