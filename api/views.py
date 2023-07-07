import datetime
import json
from os import name
from requests import delete
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
from acl.utils import user_util
from api.utils.file_type import identify_file_type 
from api.utils import shared_fxns




class FoundationViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = models.RRIGoals.objects.all().order_by('id')
    serializer_class = serializers.FetchRRIGoalsSerializer
    search_fields = ['id', ]

    def get_queryset(self):
        return []
    
    @action(methods=["POST", "GET", "PUT"],
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
            
        elif request.method == "PUT":
            payload = request.data
            serializer = serializers.UpdateDepartmentSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                name = payload['name']
                request_id = payload['request_id']

                try:
                    sector = models.Sector.objects.get(Q(id=request_id))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Sector!"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    sector.name = name
                    sector.save()

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
                    return Response(sectors, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                
    
    @action(methods=["POST", "GET",  "PUT"],
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
            
        elif request.method == "PUT":
            payload = request.data
            serializer = serializers.UpdateDepartmentSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                name = payload['name']
                request_id = payload['request_id']

                try:
                    title = models.Title.objects.get(Q(id=request_id))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown title!"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    title.name = name
                    title.save()

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
                contact = str(payload['contact'])
                title = payload['title']

                if len(contact) > 10 or len(contact) < 9:
                    return Response({"details": "Incorect contact format, use: 0700000000"}, status=status.HTTP_400_BAD_REQUEST)
                
                elif len(contact) == 10:
                    if contact[0] == '0':
                        contact = contact[1:]
                        contact = "+254" + contact
                    else:
                        return Response({"details": "Incorect contact format, use: 0700000000"}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    contact = "+254" + contact

                user_exists = models.Overseer.objects.filter(Q(contact=contact)).exists()
                if user_exists:
                    return Response({"details": "User Already Added!"}, status=status.HTTP_400_BAD_REQUEST)

                name = name.split()
                name = [x.capitalize() for x in name]
                name = " ".join(name)


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


    @action(methods=["POST", "GET", "PUT", "DELETE"],
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


                try:
                    department = models.Department.objects.get(Q(id=department))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown department!"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    sector = models.Sector.objects.get(Q(id=sector))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown sector!"}, status=status.HTTP_400_BAD_REQUEST)
                
                
                with transaction.atomic():
                    raw = {
                        "area": area,
                        "department": department,
                        "sector": sector,
                    }
                    models.ThematicArea.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":
            payload = request.data
            serializer = serializers.UpdateThematicAreaSerializer(  
                data=payload, many=False)
            if serializer.is_valid():
                request_id = payload['request_id']
                area = payload['area']
                sector = payload['sector']
                department = payload['department']
                

                try:
                    models.ThematicArea.objects.get(Q(id=request_id))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown thematic area!"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    department = models.Department.objects.get(Q(id=department))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown department!"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    sector = models.Sector.objects.get(Q(id=sector))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown sector!"}, status=status.HTTP_400_BAD_REQUEST)
                
                
                with transaction.atomic():
                    raw = {
                        "area": area,
                        "department": department,
                        "sector": sector,
                    }
                    models.ThematicArea.objects.filter(Q(id=request_id)).update(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            overseer_id = request.query_params.get('overseer_id')
            if request_id:
                try:
                    area = models.ThematicArea.objects.get(Q(id=request_id))
                    area = serializers.FetchThematicAreaSerializer(area,many=False).data
                    return Response(area, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            elif overseer_id:
                try:
                    overseer = models.ThematicArea.objects.filter((Q(results_leader=overseer_id) | Q(team_leader=overseer_id) | Q(team_leader=overseer_id)) & Q(is_deleted=False)).order_by('date_created')
                    overseer = serializers.FetchThematicAreaSerializer(overseer,many=True).data
                    return Response(overseer, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    area = models.ThematicArea.objects.filter(Q(is_deleted=False)).order_by('date_created')
                    area = serializers.FetchThematicAreaSerializer(area,many=True).data
                    return Response(area, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
            with transaction.atomic():
                raw = {"is_deleted" : True}
                models.ThematicArea.objects.filter(Q(id=request_id)).update(**raw)
                return Response('200', status=status.HTTP_200_OK)
            


    @action(methods=["POST", "GET", "PUT"],
            detail=False,
            url_path="rri-goals",
            url_name="rri-goals")
    def rri_goals(self, request):
        if request.method == "POST":
            payload = request.data
            serializer = serializers.CreateRRIGoalsSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                wave = payload['wave']
                goal = payload['goal']
                coach = payload['coach']
                thematic_area = payload['thematic_area']
                results_leader = payload['results_leader']
                team_leader = payload['team_leader']
                strategic_leader = payload['strategic_leader']

                try:
                    thematic_area = models.ThematicArea.objects.get(Q(id=thematic_area))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown thematic area!"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    coach = models.Overseer.objects.get(Q(id=coach))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown coach!"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    wave = models.Wave.objects.get(Q(id=wave))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown wave!"}, status=status.HTTP_400_BAD_REQUEST)
                
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
                        "wave": wave,
                        "goal": goal,
                        "coach": coach,
                        "thematic_area": thematic_area,
                        "results_leader": results_leader,
                        "team_leader": team_leader,
                        "strategic_leader": strategic_leader,
                    }
                    rri = models.RRIGoals.objects.create(**raw)

                    team_members = payload['team_members']
                    if team_members:
                        if isinstance(team_members, list):
                            for member in team_members:
                                raw = {
                                    "name": member,
                                    "goal": rri
                                }
                                models.TeamMembers.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":
            payload = request.data
            serializer = serializers.UpdateRRIGoalsSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                wave = payload['wave']
                goal = payload['goal']
                coach = payload['coach']
                thematic_area = payload['thematic_area']
                request_id = payload['request_id']
                results_leader = payload['results_leader']
                team_leader = payload['team_leader']
                strategic_leader = payload['strategic_leader']

                try:
                    rri = models.RRIGoals.objects.get(Q(id=request_id))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request!"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    thematic_area = models.ThematicArea.objects.get(Q(id=thematic_area))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown thematic area!"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    coach = models.Overseer.objects.get(Q(id=coach))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown coach!"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    wave = models.Wave.objects.get(Q(id=wave))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown wave!"}, status=status.HTTP_400_BAD_REQUEST)
                

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
                        "wave": wave,
                        "goal": goal,
                        "coach": coach,
                        "thematic_area": thematic_area,
                        "results_leader": results_leader,
                        "team_leader": team_leader,
                        "strategic_leader": strategic_leader,
                    }
                    models.RRIGoals.objects.filter(Q(id=request_id)).update(**raw)

                    # update team members
                    team_members = payload['team_members']
                    if team_members:
                        # delete existing members
                        models.TeamMembers.objects.filter(Q(goal=request_id)).delete()
                        # save new members
                        if isinstance(team_members, list):
                            for member in team_members:
                                raw = {
                                    "name": member,
                                    "goal": rri
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
                name = payload['member']
                thematic_area = payload['thematic_area']

                try:
                    thematic_area = models.ThematicArea.objects.get(Q(id=thematic_area))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown thematic area!"}, status=status.HTTP_400_BAD_REQUEST)
                
                name = name.split()
                name = [x.capitalize() for x in name]
                name = " ".join(name)
                                
                
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
                
                
    @action(methods=["POST"], detail=False, url_path="achievements",url_name="achievements")
    def achievements(self, request):
        authenticated_user = request.user
        formfiles = request.FILES

        payload = json.loads(request.data['payload'])
        serializer = serializers.CreateEvidenceSerializer(
                data=payload, many=False)
        if serializer.is_valid():
            description = payload['description']
            thematic_area = payload['thematic_area_id']
            category = payload['upload_status']

            try:
                thematic_area = models.ThematicArea.objects.get(Q(id=thematic_area))
            except (ValidationError, ObjectDoesNotExist):
                return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            
            if formfiles:
                exts = ['jpeg','jpg','png','tiff','pdf']
                for f in request.FILES.getlist('documents'):
                    original_file_name = f.name
                    ext = original_file_name.split('.')[1].strip().lower()
                    if ext not in exts:
                        return Response({"details": "Only Images and PDFs allowed for upload!"}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                achievement = models.Achievement.objects.create(
                    creator=authenticated_user, description=description, thematic_area=thematic_area, category=category)

                if formfiles:                        
                    for f in request.FILES.getlist('documents'):
                        file_type = shared_fxns.identify_file_type(original_file_name.split('.')[1].strip().lower())
                        try:
                            original_file_name = f.name                            
                            models.AchievementDocuments.objects.create(
                                        document=f, original_file_name=original_file_name, 
                                        achievement=achievement, file_type=file_type)

                        except Exception as e:
                            # logger.error(e)
                            print(e)
                            return Response({"details": "Invalid File(s)"}, status=status.HTTP_400_BAD_REQUEST)  
                                            

            user_util.log_account_activity(
                authenticated_user, authenticated_user, "Evidence created", "Evidence Creation Executed")
            return Response('success', status=status.HTTP_200_OK)
        
        else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        

    
    @action(methods=["POST", "GET",  "PUT"],
            detail=False,
            url_path="waves",
            url_name="waves")
    def waves(self, request):
        if request.method == "POST":
            payload = request.data
            
            serializer = serializers.CreateWaveSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                name = payload['name']
                start_date = payload['start_date']
                end_date = payload['end_date']
                lead_coach = payload['lead_coach']

                # check existance of same wave name
                if models.Wave.objects.filter(name__icontains=name).exists():
                    return Response({"details": f"{name} already exists!"}, status=status.HTTP_400_BAD_REQUEST) 

                # validate lead coach
                try:
                    lead_coach = get_user_model().objects.get(Q(id=lead_coach))
                except Exception as e:
                    print(e)
                    return Response({"details": "Unknown Lead Coach"}, status=status.HTTP_400_BAD_REQUEST) 
                    

                # find difference in dates / validate dates
                days = shared_fxns.find_date_difference(start_date,end_date,'days')
                            
                try:
                    days = int(days)
                except Exception as e:
                    return Response({"details": f"Invalid dates!"}, status=status.HTTP_400_BAD_REQUEST) 
                
                if days < 100 or days < 0:
                    return Response({"details": f"Period is less than 100 days!"}, status=status.HTTP_400_BAD_REQUEST) 

                

                with transaction.atomic():
                    raw = {
                        "name": name,
                        "start_date": start_date,
                        "end_date": end_date,
                        "lead_coach": lead_coach,
                    }
                    models.Wave.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":
            payload = request.data
            serializer = serializers.UpdateWaveSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                name = payload['name']
                start_date = payload['start_date']
                end_date = payload['end_date']
                lead_coach = payload['lead_coach']
                request_id = payload['request_id']

                try:
                    wave = models.Wave.objects.get(Q(id=request_id))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown wave!"}, status=status.HTTP_400_BAD_REQUEST)
                
                # validate lead coach
                try:
                    lead_coach = get_user_model().objects.get(Q(id=lead_coach))
                except Exception as e:
                    print(e)
                    return Response({"details": "Unknown Lead Coach"}, status=status.HTTP_400_BAD_REQUEST) 
                
                with transaction.atomic():
                    wave.name = name
                    wave.start_date = start_date
                    wave.end_date = end_date
                    wave.lead_coach = lead_coach
                    wave.save()

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    wave = models.Wave.objects.get(Q(id=request_id))
                    wave = serializers.FetchWaveSerializer(wave,many=False).data
                    return Response(wave, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown wave!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    waves = models.Wave.objects.all().order_by('name')
                    waves = serializers.FetchWaveSerializer(waves,many=True).data
                    return Response(waves, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                
            
    @action(methods=["GET","POST", "PUT"], detail=False, url_path="weekly-reports",url_name="weekly-reports")
    def weekly_reports(self, request):
        authenticated_user = request.user
        payload = request.data
        
        if request.method == "POST":
            serializer = serializers.WeeklyReportSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                milestone = payload['milestone']
                rri_goal = payload['rri_goal']
                steps = payload['steps']
                start_date = payload['start_date']
                end_date = payload['end_date']


                if not steps:
                    return Response({"details": f"Action steps required!"}, status=status.HTTP_400_BAD_REQUEST) 
                

                # find difference in dates / validate dates
                days = shared_fxns.find_date_difference(start_date,end_date,'days')
                            
                try:
                    days = int(days)
                except Exception as e:
                    return Response({"details": f"Invalid dates !"}, status=status.HTTP_400_BAD_REQUEST) 
                
                if days < 7:
                    return Response({"details": f"Period is less than a week !"}, status=status.HTTP_400_BAD_REQUEST) 
                elif days > 7:
                    return Response({"details": f"Period is beyond a week !"}, status=status.HTTP_400_BAD_REQUEST) 

                try:
                    rri_goal = models.RRIGoals.objects.get(Q(id=rri_goal))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown RRI Goal !"}, status=status.HTTP_400_BAD_REQUEST)
                
                
                with transaction.atomic():
                    raw = {
                        "start_date" : start_date,
                        "end_date" : end_date,
                        "milestone" : milestone,
                        "rri_goal" : rri_goal,
                        "steps" : steps,
                        "creator": authenticated_user
                    }

                    report = models.WeeklyReports.objects.create(**raw)
                                                

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Weekly Report created", f"Weekly Report Creation Executed: {report.id}")
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                    return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == "PUT":
            serializer = serializers.UpdateWeeklyReportSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                milestone = payload['milestone']
                rri_goal = payload['rri_goal']
                steps = payload['steps']
                start_date = payload['start_date']
                end_date = payload['end_date']

                # find difference in dates / validate dates
                days = shared_fxns.find_date_difference(start_date,end_date,'days')
                            
                try:
                    days = int(days)
                except Exception as e:
                    return Response({"details": f"Invalid dates !"}, status=status.HTTP_400_BAD_REQUEST) 
                
                if days < 7:
                    return Response({"details": f"Period is less than a week !"}, status=status.HTTP_400_BAD_REQUEST) 
                elif days > 7:
                    return Response({"details": f"Period is beyond a week !"}, status=status.HTTP_400_BAD_REQUEST) 

                try:
                    rri_goal = models.RRIGoals.objects.get(Q(id=rri_goal))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Thematic Area!"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    models.WeeklyReports.objects.get(Q(id=request_id))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Report!"}, status=status.HTTP_400_BAD_REQUEST)
                
                
                with transaction.atomic():
                    raw = {
                        "start_date" : start_date,
                        "end_date" : end_date,
                        "milestone" : milestone,
                        "rri_goal" : rri_goal,
                        "steps" : steps,
                        "creator": authenticated_user
                    }

                    # report = models.WeeklyReports.objects.update(**raw)
                    models.WeeklyReports.objects.filter(Q(id=request_id)).update(**raw)
                                                

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Weekly Report updated", f"Weekly Report updation Executed: {report.id}")
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                    return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            rri_goal = request.query_params.get('rri_goal')
            if request_id:
                try:
                    report = models.WeeklyReports.objects.get(Q(id=request_id))
                    report = serializers.FetchWeeklyReportSerializer(report,many=False).data
                    return Response(report, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            elif rri_goal:
                try:
                    reports = models.WeeklyReports.objects.filter(Q(rri_goal=rri_goal)).order_by('-date_created')
                    reports = serializers.FetchWeeklyReportSerializer(reports,many=True).data
                    return Response(reports, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    reports = models.WeeklyReports.objects.all().order_by('-date_created')
                    reports = serializers.FetchWeeklyReportSerializer(reports,many=True).data
                    return Response(reports, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                
        
    @action(methods=["GET","POST", "PUT"], detail=False, url_path="workplan",url_name="workplan")
    def workplan(self, request):
        authenticated_user = request.user
        payload = request.data
        
        if request.method == "POST":
            serializer = serializers.WWorkPlanSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                milestone = payload['milestone']
                rri_goal = payload['rri_goal']
                steps = payload['steps']
                start_date = payload['start_date']
                end_date = payload['end_date']
                budget = payload['budget']
                plan_status = payload['status']
                remarks = payload['remarks']


                if not steps:
                    return Response({"details": f"Action steps required!"}, status=status.HTTP_400_BAD_REQUEST) 
                

                # find difference in dates / validate dates
                days = shared_fxns.find_date_difference(start_date,end_date,'days')

                try:
                    budget = int(budget)
                except Exception as e:
                    return Response({"details": f"Invalid budget format !"}, status=status.HTTP_400_BAD_REQUEST) 
                            
                try:
                    days = int(days)
                except Exception as e:
                    return Response({"details": f"Invalid dates !"}, status=status.HTTP_400_BAD_REQUEST) 
                
                if days < 0:
                    return Response({"details": f"Invalid dates entered !"}, status=status.HTTP_400_BAD_REQUEST) 

                try:
                    rri_goal = models.RRIGoals.objects.get(Q(id=rri_goal))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown RRI Goal !"}, status=status.HTTP_400_BAD_REQUEST)
                
                
                with transaction.atomic():
                    raw = {
                        "start_date" : start_date,
                        "end_date" : end_date,
                        "milestone" : milestone,
                        "rri_goal" : rri_goal,
                        "steps" : steps,
                        "creator": authenticated_user,
                        "budget": budget,
                        "remarks": remarks,
                        "status": plan_status,
                    }

                    plan = models.WorkPlan.objects.create(**raw)
                                                

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Workplan created", f"Workplan Creation Executed: {plan.id}")
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                    return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == "PUT":
            serializer = serializers.UpdateWWorkPlanSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                milestone = payload['milestone']
                rri_goal = payload['rri_goal']
                steps = payload['steps']
                start_date = payload['start_date']
                end_date = payload['end_date']
                budget = payload['budget']
                plan_status = payload['status']
                remarks = payload['remarks']


                # find difference in dates / validate dates
                days = shared_fxns.find_date_difference(start_date,end_date,'days')
                            
                try:
                    days = int(days)
                except Exception as e:
                    return Response({"details": f"Invalid dates !"}, status=status.HTTP_400_BAD_REQUEST) 
                
                try:
                    budget = int(budget)
                except Exception as e:
                    return Response({"details": f"Invalid budget format !"}, status=status.HTTP_400_BAD_REQUEST) 
                
                if days < 0:
                    return Response({"details": f"Invalid dates entered !"}, status=status.HTTP_400_BAD_REQUEST) 

                try:
                    rri_goal = models.RRIGoals.objects.get(Q(id=rri_goal))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown RRI Goal!"}, status=status.HTTP_400_BAD_REQUEST)
                
                
                with transaction.atomic():
                    raw = {
                        "start_date" : start_date,
                        "end_date" : end_date,
                        "milestone" : milestone,
                        "rri_goal" : rri_goal,
                        "steps" : steps,
                        "creator": authenticated_user,
                        "budget": budget,
                        "remarks": remarks,
                        "status": plan_status,
                    }

                    models.WorkPlan.objects.filter(Q(id=request_id)).update(**raw)
                                                

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Workplan updated", f"Workplan updation Executed: {request_id}")
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                    return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            rri_goal = request.query_params.get('rri_goal')
            if request_id:
                try:
                    worplan = models.WorkPlan.objects.get(Q(id=request_id))
                    worplan = serializers.FetchWorkPlanSerializer(worplan,many=False).data
                    return Response(worplan, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            elif rri_goal:
                try:
                    worplans = models.WorkPlan.objects.filter(Q(rri_goal=rri_goal)).order_by('-date_created')
                    worplans = serializers.FetchWorkPlanSerializer(worplans,many=True).data
                    return Response(worplans, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    worplans = models.WorkPlan.objects.all().order_by('-date_created')
                    worplans = serializers.FetchWorkPlanSerializer(worplans,many=True).data
                    return Response(worplans, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                

    @action(methods=["GET","POST", "PUT"], detail=False, url_path="results-chain",url_name="results-chain")
    def resultchain(self, request):
        authenticated_user = request.user
        payload = request.data
        
        if request.method == "POST":
            serializer = serializers.ResultChainSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                rri_goal = payload['rri_goal']
                activities = payload['activities']
                input = payload['input']
                output = payload['output']
                outcome = payload['outcome']
                impact = payload['impact']


                if not activities:
                    return Response({"details": f"Activities required !"}, status=status.HTTP_400_BAD_REQUEST) 
                if not input:
                    return Response({"details": f"Inputs required !"}, status=status.HTTP_400_BAD_REQUEST) 
                if not output:
                    return Response({"details": f"Outputs required !"}, status=status.HTTP_400_BAD_REQUEST) 
                if not outcome:
                    return Response({"details": f"Outcomes required !"}, status=status.HTTP_400_BAD_REQUEST) 
                if not impact:
                    return Response({"details": f"Impacts required !"}, status=status.HTTP_400_BAD_REQUEST) 

                try:
                    rri_goal = models.RRIGoals.objects.get(Q(id=rri_goal))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown RRI Goal !"}, status=status.HTTP_400_BAD_REQUEST)
                
                
                with transaction.atomic():
                    raw = {
                        "rri_goal" : rri_goal,
                        "activities" : activities,
                        "creator": authenticated_user,
                        "input": input,
                        "output": output,
                        "outcome": outcome,
                        "impact": impact,
                    }

                    chain = models.ResultChain.objects.create(**raw)
                                                

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "ResultChain created", f"ResultChain Creation Executed: {chain.id}")
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                    return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == "PUT":
            serializer = serializers.UpdateResultChainSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                rri_goal = payload['rri_goal']
                activities = payload['activities']
                input = payload['input']
                output = payload['output']
                outcome = payload['outcome']
                impact = payload['impact']

                if not activities:
                    return Response({"details": f"Activities required !"}, status=status.HTTP_400_BAD_REQUEST) 

                try:
                    rri_goal = models.RRIGoals.objects.get(Q(id=rri_goal))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown RRI Goal!"}, status=status.HTTP_400_BAD_REQUEST)          
                
                
                with transaction.atomic():
                    raw = {
                        "rri_goal" : rri_goal,
                        "activities" : activities,
                        "creator": authenticated_user,
                        "input": input,
                        "output": output,
                        "outcome": outcome,
                        "impact": impact,
                    }

                    models.ResultChain.objects.filter(Q(id=request_id)).update(**raw)
                                                

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "ResultChain updated", f"ResultChain updation Executed: {request_id}")
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                    return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            rri_goal = request.query_params.get('rri_goal')
            if request_id:
                try:
                    chain = models.ResultChain.objects.get(Q(id=request_id))
                    chain = serializers.FetchResultChainSerializer(chain,many=False).data
                    return Response(chain, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            elif rri_goal:
                try:
                    chains = models.ResultChain.objects.filter(Q(rri_goal=rri_goal)).order_by('-date_created')
                    chains = serializers.FetchResultChainSerializer(chains,many=True).data
                    return Response(chains, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    chains = models.ResultChain.objects.all().order_by('-date_created')
                    chains = serializers.FetchResultChainSerializer(chains,many=True).data
                    return Response(chains, status=status.HTTP_200_OK)
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
