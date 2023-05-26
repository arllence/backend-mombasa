from rest_framework.routers import DefaultRouter
from api import views

router = DefaultRouter(trailing_slash=False)

router.register('foundation',views.FoundationViewSet, basename='foundation')
router.register('department',views.DepartmentViewSet, basename='department')
   
                         
urlpatterns = router.urls