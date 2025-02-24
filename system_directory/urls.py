from rest_framework.routers import DefaultRouter
from system_directory import views

router = DefaultRouter(trailing_slash=False)

router.register('directory-generics', views.GenericsViewSet, basename='directory-generics')
router.register('directory-links', views.QuickLinksViewSet, basename='directory-links')
   
                         
urlpatterns = router.urls