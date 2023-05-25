from rest_framework.routers import DefaultRouter
from api import views

router = DefaultRouter(trailing_slash=False)

router.register('foundation',views.FoundationViewSet, basename='foundation')
   
                         
urlpatterns = router.urls