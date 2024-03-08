from rest_framework.routers import DefaultRouter
from mms import views

router = DefaultRouter(trailing_slash=False)

router.register('mms',views.MmsViewSet, basename='mms')
# router.register('department',views.DepartmentViewSet, basename='department')
# router.register('reports',views.ReportsViewSet, basename='reports')
# router.register('analytics',views.AnalyticsViewSet, basename='analytics')
   
                         
urlpatterns = router.urls