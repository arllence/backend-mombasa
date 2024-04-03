from rest_framework.routers import DefaultRouter
from acl import views

router = DefaultRouter(trailing_slash=False)

router.register('acl',views.AuthenticationViewSet, basename='acl')
router.register('account-management',
                views.AccountManagementViewSet, basename='account-management')
router.register('ict-support',
                views.ICTSupportViewSet, basename='ict-support')   
router.register('department',
                views.DepartmentViewSet, basename='department')
router.register('slt',
                views.SltViewSet, basename='slt')
   
                         
urlpatterns = router.urls