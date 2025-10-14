from rest_framework.routers import DefaultRouter
from security_helpdesk import views

router = DefaultRouter(trailing_slash=False)

router.register('security-helpdesk', views.HelpDeskViewSet, basename='security-helpdesk')
router.register('security-helpdesk-reports',views.ReportsViewSet, basename='security-helpdesk-reports')
router.register('security-helpdesk-analytics',views.AnalyticsViewSet, basename='security-helpdesk-analytics')
router.register('security-helpdesk-generics',views.GenericsViewSet, basename='security-helpdesk-generics')
   
                         
urlpatterns = router.urls