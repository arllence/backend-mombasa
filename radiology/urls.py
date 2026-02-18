from rest_framework.routers import DefaultRouter
from radiology import views
from django.urls import path

router = DefaultRouter(trailing_slash=False)

router.register('radiology', views.CoreViewSet, basename='radiology')
# router.register('radiology-reports',views.ReportsViewSet, basename='radiology-reports')
# router.register('radiology-analytics',views.AnalyticsViewSet, basename='radiology-analytics')


router.register(r"radiology/shifts", views.ShiftViewSet, basename="shift")


# urlpatterns = [
#     path("radiology/shifts/", views.ShiftCreateAPIView.as_view()),
#     path("radiology/shifts/<uuid:shift_id>/rooms/", views.RoomStatusCreateAPIView.as_view()),
#     path("radiology/shifts/<uuid:shift_id>/equipment/", views.EquipmentStatusCreateAPIView.as_view()),
#     path("radiology/shifts/<uuid:shift_id>/pending/", views.PendingCaseCreateAPIView.as_view()),
#     path("radiology/shifts/<uuid:shift_id>/critical/", views.CriticalResultCreateAPIView.as_view()),
#     path("radiology/shifts/<uuid:shift_id>/stock/", views.StockEntryCreateAPIView.as_view()),
#     path("radiology/shifts/<uuid:shift_id>/infection/", views.InfectionControlCreateAPIView.as_view()),
#     path("radiology/shifts/<uuid:shift_id>/nurse/", views.NurseHandoverCreateAPIView.as_view()),
#     path("radiology/shifts/<uuid:shift_id>/sign-out/", views.ShiftSignOutAPIView.as_view()),
#     path("radiology/shifts/<uuid:shift_id>/confirm/", views.ShiftConfirmAPIView.as_view()),
# ]
   
                         
urlpatterns = router.urls