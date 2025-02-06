from rest_framework.routers import DefaultRouter
from mhs import views

router = DefaultRouter(trailing_slash=False)

router.register('mhs', views.MHSViewSet, basename='mhs')
router.register('mhs-reports',views.ReportsViewSet, basename='mhs-reports')
router.register('mhs-analytics',views.AnalyticsViewSet, basename='mhs-analytics')
router.register('mhs-generics',views.GenericsViewSet, basename='mhs-generics')
   
                         
urlpatterns = router.urls