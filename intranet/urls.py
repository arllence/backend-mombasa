from rest_framework.routers import DefaultRouter
from intranet import views

router = DefaultRouter(trailing_slash=False)

router.register('document-manager', views.DocumentManagerViewSet, basename='document-manager')
router.register('quick-links', views.QuickLinksViewSet, basename='quick-links')
router.register('generics', views.GenericsViewSet, basename='generics')
router.register('qips', views.QipsViewSet, basename='qips')
router.register('intranet-departments', views.DepartmentsViewSet, basename='intranet-departments')
router.register('survey', views.SurveyViewSet, basename='survey')
router.register('module', views.ModuleViewSet, basename='module')
router.register('privileges', views.PrivilegesViewSet, basename='privileges')
# router.register('s3-reports',views.ReportsViewSet, basename='s3-reports')
# router.register('s3-analytics',views.AnalyticsViewSet, basename='s3-analytics')
   
                         
urlpatterns = router.urls