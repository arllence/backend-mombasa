from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.contrib.auth import get_user_model
from django.db.models import  Q
from django.db import transaction
from api import models
from api import serializers
from django.db import IntegrityError, DatabaseError




class FoundationViewSet(viewsets.ModelViewSet):
    permission_classes = (AllowAny)
    queryset = models.RRIGoals.objects.all().order_by('id')
    serializer_class = serializers.FetchRRIGoalsSerializer
    search_fields = ['id', ]

    def get_queryset(self):
        return []
    
    @action(methods=["POST", "GET"],
            detail=False,
            url_path="sector",
            url_name="sector")
    def sector(self, request):
        if request.method == "POST":
            payload = request.data
            serializer = serializers.GeneralNameSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                name = payload['name']
                with transaction.atomic():
                    raw = {
                        "name":name
                    }
                    models.Sector.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    sector = models.Sector.objects.get(Q(id=request_id))
                    sector = serializers.FetchSectorSerializer(sector,many=False).data
                    return Response(sector, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Sector!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    sectors = models.Sector.objects.all().order_by('name')
                    sectors = serializers.FetchSectorSerializer(sectors,many=True).data
                    return Response(sector, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                
    
    @action(methods=["POST", "GET"],
            detail=False,
            url_path="title",
            url_name="title")
    def title(self, request):
        if request.method == "POST":
            payload = request.data
            serializer = serializers.GeneralNameSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                name = payload['name']
                with transaction.atomic():
                    raw = {
                        "name": name
                    }
                    models.Title.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    title = models.Title.objects.get(Q(id=request_id))
                    title = serializers.FetchTitleSerializer(title,many=False).data
                    return Response(title, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown title!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    titles = models.Title.objects.all().order_by('name')
                    titles = serializers.FetchTitleSerializer(titles,many=True).data
                    return Response(titles, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                

    @action(methods=["POST", "GET"],
            detail=False,
            url_path="overseer",
            url_name="overseer")
    def overseer(self, request):
        if request.method == "POST":
            payload = request.data
            serializer = serializers.CreateOverseerSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                name = payload['name']
                contact = payload['contact']
                title = payload['title']

                if len(contact) > 10 or len(contact) < 10:
                    return Response({"details": "Incorect contact format, use: 0700000000"}, status=status.HTTP_400_BAD_REQUEST)


                try:
                    title = models.Title.objects.get(Q(id=title))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown title!"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    raw = {
                        "name": name,
                        "contact": contact,
                        "title": title,
                    }
                    models.Overseer.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            name = request.query_params.get('name')
            if request_id:
                try:
                    overseer = models.Overseer.objects.get(Q(id=request_id))
                    overseer = serializers.FetchOverseerSerializer(overseer,many=False).data
                    return Response(overseer, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Overseer!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            elif name:
                try:
                    overseer = models.Overseer.objects.filter(Q(name=name)).order_by('name')
                    overseer = serializers.FetchOverseerSerializer(overseer,many=True).data
                    return Response(overseer, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    overseer = models.Overseer.objects.all().order_by('name')
                    overseer = serializers.FetchOverseerSerializer(overseer,many=True).data
                    return Response(overseer, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)


    @action(methods=["POST", "GET"],
            detail=False,
            url_path="thematic-areas",
            url_name="thematic-areas")
    def thematic_areas(self, request):
        if request.method == "POST":
            payload = request.data
            serializer = serializers.CreateThematicAreaSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                area = payload['area']
                sector = payload['sector']
                department = payload['department']
                results_leader = payload['results_leader']
                team_leader = payload['team_leader']
                strategic_leader = payload['strategic_leader']


                try:
                    department = models.Department.objects.get(Q(id=department))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown department!"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    sector = models.Overseer.objects.get(Q(id=sector))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown sector!"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    results_leader = models.Overseer.objects.get(Q(id=results_leader))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown overseer!"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    team_leader = models.Overseer.objects.get(Q(id=team_leader))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown overseer!"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    strategic_leader = models.Overseer.objects.get(Q(id=strategic_leader))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown overseer!"}, status=status.HTTP_400_BAD_REQUEST)
                
                
                with transaction.atomic():
                    raw = {
                        "area": area,
                        "results_leader": results_leader,
                        "team_leader": team_leader,
                        "strategic_leader": strategic_leader,
                        "department": department,
                        "sector": sector,
                    }
                    models.ThematicArea.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            overseer_id = request.query_params.get('overseer_id')
            if request_id:
                try:
                    area = models.ThematicArea.objects.get(Q(id=request_id))
                    area = serializers.FetchThematicSerializer(area,many=False).data
                    return Response(area, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            elif overseer_id:
                try:
                    overseer = models.ThematicArea.objects.filter(Q(results_leader=overseer_id) | Q(team_leader=overseer_id) | Q(team_leader=overseer_id)).order_by('date_created')
                    overseer = serializers.FetchThematicSerializer(overseer,many=True).data
                    return Response(overseer, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    area = models.ThematicArea.objects.all().order_by('date_created')
                    area = serializers.FetchThematicAreaSerializer(area,many=True).data
                    return Response(area, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)


    @action(methods=["POST", "GET"],
            detail=False,
            url_path="rri-goals",
            url_name="rri-goals")
    def rri_goals(self, request):
        if request.method == "POST":
            payload = request.data
            serializer = serializers.CreateRRIGoalsSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                goal = payload['goal']
                thematic_area = payload['thematic_area']

                try:
                    thematic_area = models.ThematicArea.objects.get(Q(id=thematic_area))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown thematic area!"}, status=status.HTTP_400_BAD_REQUEST)
                                
                
                with transaction.atomic():
                    raw = {
                        "goal": goal,
                        "thematic_area": thematic_area
                    }
                    models.RRIGoals.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            thematic_area = request.query_params.get('thematic_area')
            if request_id:
                try:
                    rri = models.RRIGoals.objects.get(Q(id=request_id))
                    rri = serializers.FetchRRIGoalsSerializer(rri,many=False).data
                    return Response(rri, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            elif thematic_area:
                try:
                    area = models.RRIGoals.objects.filter(Q(thematic_area=thematic_area)).order_by('date_created')
                    area = serializers.FetchRRIGoalsSerializer(area,many=True).data
                    return Response(area, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    area = models.RRIGoals.objects.all().order_by('date_created')
                    area = serializers.FetchRRIGoalsSerializer(area,many=True).data
                    return Response(area, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)



    @action(methods=["POST", "GET"],
            detail=False,
            url_path="team-members",
            url_name="team-members")
    def team_members(self, request):
        if request.method == "POST":
            payload = request.data
            serializer = serializers.CreateTeamMembersSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                name = payload['name']
                thematic_area = payload['thematic_area']

                try:
                    thematic_area = models.ThematicArea.objects.get(Q(id=thematic_area))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown thematic area!"}, status=status.HTTP_400_BAD_REQUEST)
                                
                
                with transaction.atomic():
                    raw = {
                        "name": name,
                        "thematic_area": thematic_area
                    }
                    models.TeamMembers.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            thematic_area = request.query_params.get('thematic_area')
            if request_id:
                try:
                    members = models.TeamMembers.objects.get(Q(id=request_id))
                    members = serializers.FetchTeamMembersSerializer(members,many=False).data
                    return Response(members, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            elif thematic_area:
                try:
                    members = models.TeamMembers.objects.filter(Q(thematic_area=thematic_area)).order_by('name')
                    members = serializers.FetchTeamMembersSerializer(members,many=True).data
                    return Response(members, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    members = models.TeamMembers.objects.all().order_by('name')
                    members = serializers.FetchTeamMembersSerializer(members,many=True).data
                    return Response(members, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                


class DepartmentViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = models.Department.objects.all().order_by('id')
    serializer_class = serializers.CreateDepartmentSerializer
    search_fields = ['id', ]

    def get_queryset(self):
        return []

    @action(methods=["POST", "GET", "PUT"],
            detail=False,
            url_path="department",
            url_name="department")
    def department(self, request):
        if request.method == "POST":
            payload = request.data
            serializer = serializers.GeneralNameSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                name = payload['name']
                with transaction.atomic():
                    raw = {
                        "name": name
                    }
                    models.Department.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":
            payload = request.data
            serializer = serializers.UpdateDepartmentSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                dept_id = payload['request_id']
                name = payload['name']
                with transaction.atomic():
                    try:
                        dept = models.Department.objects.get(id=dept_id)
                        dept.name = name
                        dept.save()
                    except (ValidationError, ObjectDoesNotExist):
                        return Response({"details": "Unknown department!"}, status=status.HTTP_400_BAD_REQUEST)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    department = models.Department.objects.get(Q(id=request_id))
                    department = serializers.FetchDepartmentSerializer(department,many=False).data
                    return Response(department, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown department!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    departments = models.Department.objects.all().order_by('name')
                    departments = serializers.FetchDepartmentSerializer(departments,many=True).data
                    return Response(departments, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
