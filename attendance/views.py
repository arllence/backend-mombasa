import logging
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny

from . import state, bootstrap

# Get an instance of a logger
logger = logging.getLogger(__name__)

class GenericsViewSet(viewsets.ViewSet):
    permission_classes = (AllowAny,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["GET"], detail=False, url_path="attendance-health",url_name="attendance-health")
    def health(request):
        last = state.get_last_success()
        age = state.seconds_since_success()
        return Response({
            "fresh": state.is_fresh(),
            "clone_detected": state.is_clone_detected(),
            "last_success_unix": last,
            "age_seconds": None if age == float("inf") else age,
            "max_age_seconds": state.MAX_AGE_SECONDS,
            "bootstrap_remaining_seconds": (
                None if bootstrap.get_bootstrap_timestamp() is None
                else max(0, bootstrap.seconds_until_bootstrap_expires())
            ),
        }, status=status.HTTP_200_OK)
    
   


