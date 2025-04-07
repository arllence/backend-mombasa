from rest_framework.routers import DefaultRouter
from ict_helpdesk import views

router = DefaultRouter(trailing_slash=False)

router.register('ict-helpdesk', views.HelpDeskViewSet, basename='ict-helpdesk')
router.register('ict-helpdesk-reports',views.ReportsViewSet, basename='ict-helpdesk-reports')
router.register('ict-helpdesk-analytics',views.AnalyticsViewSet, basename='ict-helpdesk-analytics')
router.register('ict-helpdesk-generics',views.GenericsViewSet, basename='ict-helpdesk-generics')
   
                         
urlpatterns = router.urls