from rest_framework.routers import DefaultRouter
from acl import views

router = DefaultRouter(trailing_slash=False)

router.register('acl',views.AuthenticationViewSet, basename='acl')
   
                         
urlpatterns = router.urls