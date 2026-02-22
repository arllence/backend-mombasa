import datetime
import json
import logging
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, JSONParser
from django.contrib.auth.hashers import make_password
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.contrib.auth import get_user_model
from django.db.models import  Q
from django.db import transaction
from radiology import models
from radiology import serializers
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import Hods, Slt, User, Sendmail, SRRSDepartment, SubDepartment, OHC
from radiology.utils import shared_fxns
from django.db.models import Sum
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import Group

from rest_framework.pagination import PageNumberPagination
# from django_filters.rest_framework import DjangoFilterBackend

# Get an instance of a logger
logger = logging.getLogger(__name__)



# 1️⃣ Create Shift
class ShiftCreateAPIView(APIView):

    def post(self, request):
        serializer = serializers.ShiftSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                outgoing_officer=request.user,
                status="DRAFT"
            )
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)

# 2️⃣ Add Room Status (Bulk)
class RoomStatusCreateAPIView(APIView):

    def post(self, request, shift_id):
        shift = get_object_or_404(models.Shift, id=shift_id)

        if shift.status != "DRAFT":
            return Response({"error": "Shift locked"}, status=400)

        serializer = serializers.RoomStatusSerializer(data=request.data, many=True)

        if serializer.is_valid():
            serializer.save(shift=shift)
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)

# 3️⃣ Equipment Status (Bulk)
class EquipmentStatusCreateAPIView(APIView):

    def post(self, request, shift_id):
        shift = get_object_or_404(models.Shift, id=shift_id)

        if shift.status != "DRAFT":
            return Response({"error": "Shift locked"}, status=400)

        serializer = serializers.EquipmentStatusSerializer(data=request.data, many=True)

        if serializer.is_valid():
            serializer.save(shift=shift)
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)

# 4️⃣ Add Pending Case
class PendingCaseCreateAPIView(APIView):

    def post(self, request, shift_id):
        shift = get_object_or_404(models.Shift, id=shift_id)

        if shift.status != "DRAFT":
            return Response({"error": "Shift locked"}, status=400)

        serializer = serializers.PendingCaseSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(shift=shift)
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)

# 5️⃣ Add Critical Result
class CriticalResultCreateAPIView(APIView):

    def post(self, request, shift_id):
        shift = get_object_or_404(models.Shift, id=shift_id)

        if shift.status != "DRAFT":
            return Response({"error": "Shift locked"}, status=400)

        serializer = serializers.CriticalResultSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(
                shift=shift,
                notified_at=timezone.now()
            )
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)

# 6️⃣ Stock Entry (Bulk)
class StockEntryCreateAPIView(APIView):

    def post(self, request, shift_id):
        shift = get_object_or_404(models.Shift, id=shift_id)

        if shift.status != "DRAFT":
            return Response({"error": "Shift locked"}, status=400)

        serializer = serializers.StockEntrySerializer(data=request.data, many=True)

        if serializer.is_valid():
            serializer.save(shift=shift)
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)

# 7️⃣ Infection Control
class InfectionControlCreateAPIView(APIView):

    def post(self, request, shift_id):
        shift = get_object_or_404(models.Shift, id=shift_id)

        if shift.status != "DRAFT":
            return Response({"error": "Shift locked"}, status=400)

        serializer = serializers.InfectionControlSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(shift=shift)
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)

# 8️⃣ Nurse Handover
class NurseHandoverCreateAPIView(APIView):

    def post(self, request, shift_id):
        shift = get_object_or_404(models.Shift, id=shift_id)

        if shift.status != "DRAFT":
            return Response({"error": "Shift locked"}, status=400)

        serializer = serializers.NurseHandoverSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(shift=shift)
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)

# 9️⃣ Outgoing Sign-Off
class ShiftSignOutAPIView(APIView):

    @transaction.atomic
    def post(self, request, shift_id):
        shift = get_object_or_404(models.Shift, id=shift_id)

        if shift.status != "DRAFT":
            return Response({"error": "Invalid state"}, status=400)

        shift.status = "AWAITING_CONFIRMATION"
        shift.signed_out_at = timezone.now()
        shift.save()

        return Response({"status": shift.status}, status=200)

# 🔟 Incoming Confirmation
class ShiftConfirmAPIView(APIView):

    @transaction.atomic
    def post(self, request, shift_id):
        shift = get_object_or_404(models.Shift, id=shift_id)

        if shift.status != "AWAITING_CONFIRMATION":
            return Response({"error": "Invalid state"}, status=400)

        action = request.data.get("action")

        if action == "ACCEPT":
            shift.status = "COMPLETED"
            shift.confirmed_at = timezone.now()
            shift.save()
            return Response({"status": shift.status})

        if action == "REJECT":
            shift.status = "DRAFT"
            shift.save()
            return Response({"status": shift.status})

        return Response({"error": "Invalid action"}, status=400)
    

class ShiftViewSet(viewsets.ModelViewSet):

    queryset = models.Shift.objects.all().prefetch_related(
        "rooms",
        "equipment",
        "pending_cases",
        "critical_results",
        "stock_entries"
    ).select_related(
        "infection_control",
        "nurse_handover"
    )

    serializer_class = serializers.ShiftSerializer
    # filter_backends = [DjangoFilterBackend]
    filterset_fields = ["date", "shift_type", "status"]

    # --------------------------------------------------------
    # SIGN OUT
    # --------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="sign-out")
    @transaction.atomic
    def sign_out(self, request, pk=None):

        shift = self.get_object()

        try:
            shift.sign_out()
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(self.get_serializer(shift).data)

    # --------------------------------------------------------
    # CONFIRM
    # --------------------------------------------------------

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def confirm(self, request, pk=None):

        shift = self.get_object()

        try:
            shift.confirm()
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(self.get_serializer(shift).data)


class CoreViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="get-shifts",
            url_name="get-shifts")
    def get_shifts(self, request):
        if request.method == "GET":
            request_id = request.query_params.get('request_id')
            query = request.query_params.get('q')

            if request_id:
                try:
                    resp = models.Shift.objects.get(id=request_id)
                    resp = serializers.FetchShiftSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    logger.error(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    if query == 'pending':
                        resp = models.Shift.objects.filter(
                            Q(status='PENDING') & Q(handover_to=request.user)).order_by('-date_created')
                        
                    elif query == 'assigned':
                        resp = models.Shift.objects.filter(
                            Q(handover_to=request.user)).order_by('-date_created')
                        
                    else:
                        resp = models.Shift.objects.all()

                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.SlimFetchShiftSerializer(
                        result_page, many=True, context={"user_id":request.user.id})
                    return paginator.get_paginated_response(serializer.data)
                
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
        
    

    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="platform-admins",
            url_name="platform-admins")
    def platform_admins(self, request):
        # roles = user_util.fetchusergroups(request.user.id)
        if request.method == "POST":
            payload = request.data
            serializer = serializers.PlatformAdminSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                admin = payload['admin']

                try:
                    admin = User.objects.get(id=admin)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown User"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Invalid Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                # assign RADIOLOGY role
                assign_role = user_util.award_role('RADIOLOGY', str(admin.id))
                if not assign_role:
                    return Response({"details": "Unable to assign role RADIOLOGY"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    raw = {
                        "admin": admin,
                        "created_by": request.user
                    }

                    models.PlatformAdmin.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":
            payload = request.data

            serializer = serializers.UpdatePlatformAdminSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                admin = payload['admin']

                try:
                    request = models.PlatformAdmin.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Invalid Request"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():

                    request.admin = admin
                    request.created_by = request.user
                    request.save()

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    request = models.PlatformAdmin.objects.get(Q(id=request_id))
                    request = serializers.FetchPlatformAdminSerializer(request, many=False).data
                    return Response(request, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:

                    request = models.PlatformAdmin.objects.filter(Q(is_deleted=False)).order_by('-date_created')
                    request = serializers.FetchPlatformAdminSerializer(request, many=True).data
                    return Response(request, status=status.HTTP_200_OK)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    user = models.PlatformAdmin.objects.get(id=request_id)
                    user_util.revoke_role('RADIOLOGY', str(user.admin.id))
                    user.delete()
                    return Response('200', status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request "}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"details": "Request incomplete"}, status=status.HTTP_400_BAD_REQUEST)





class ReportsViewSet(viewsets.ViewSet):
    # search_fields = ['id', ]

    def get_queryset(self):
        return []

    @action(methods=["GET",],
            detail=False,
            url_path="contracts",
            url_name="contracts")
    def contracts(self, request):
        roles = user_util.fetchusergroups(request.user.id)  
                    
        r_status = request.query_params.get('status')
        department = request.query_params.get('department')
        commencement_date = request.query_params.get('date_from')
        expiry_date = request.query_params.get('date_to')

        q_filters = Q()

        if r_status:
            if r_status == 'ACTIVE':
                q_filters &= Q(is_expired=False)

            if r_status == 'EXPIRED':
                q_filters &= Q(is_expired=True)

        if department:
            q_filters &= Q(department=department)

        if commencement_date:
            commencement_date = datetime.datetime.strptime(commencement_date, '%Y-%m-%d')
            q_filters &= Q(commencement_date=commencement_date)

        if expiry_date:
            expiry_date = datetime.datetime.strptime(expiry_date, '%Y-%m-%d')
            q_filters &= Q(expiry_date=expiry_date)

        if q_filters:
            if any(role in ['SUPERUSER','RADIOLOGY','CEO','MMD'] for role in roles):
                resp = models.Contract.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')

            elif any(role in ['SLT'] for role in roles):
                department_ids = list(SRRSDepartment.objects.filter(slt=request.user).values_list('id', flat=True).distinct())
                resp = models.Contract.objects.filter(q_filters & Q(department__in=department_ids) | Q(created_by=request.user), is_deleted=False).order_by('-date_created')

            elif any(role in ['HOD'] for role in roles):
                department_ids = list(Hods.objects.filter(hod=request.user).values_list('department_id', flat=True).distinct())
                resp = models.Contract.objects.filter(q_filters & Q(department__in=department_ids) | Q(created_by=request.user), is_deleted=False).order_by('-date_created')
        else:
        
            if any(role in ['SUPERUSER','RADIOLOGY','CEO','MMD'] for role in roles):
                resp = models.Contract.objects.filter(Q(is_deleted=False)).order_by('-date_created')[:50]
                
            else:
                resp = models.Contract.objects.filter(Q(is_deleted=False) & Q(created_by=request.user)).order_by('-date_created')[:50]


        resp = serializers.FetchContractSerializer(resp, many=True, context={"user_id":request.user.id}).data

        return Response(resp, status=status.HTTP_200_OK)
    
        
class AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return []

    @action(methods=["GET",],
            detail=False,
            url_path="general",
            url_name="general")
    def general(self, request):
   
        # Get the current date
        now = timezone.now().date()

        # Calculate the date 4 months from now
        four_months_from_now = now + timedelta(days=4*30)  # Approximating 4 months as 120 days

        total = models.Contract.objects.filter(Q(is_deleted=False)).count()
        almost = models.Contract.objects.filter(Q(is_deleted=False),expiry_date__gte=now, expiry_date__lte=four_months_from_now).count()
        expired = models.Contract.objects.filter(Q(is_deleted=False),expiry_date__lt=now).count()
        renewed = models.Contract.objects.filter(Q(is_deleted=False)).exclude(previous__isnull=False).count()

        resp = {
            "total": total,
            "almost": almost,
            "expired": expired,
            "renewed": renewed,
        }

        return Response(resp, status=status.HTTP_200_OK)