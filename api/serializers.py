from django.db.models import  Q
from acl.serializers import UsersSerializer
from api import models as api_models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError




class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)


class FetchSectorSerializer(serializers.ModelSerializer):

    class Meta:
        model = api_models.Sector
        fields = '__all__'


class UpdateDepartmentSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)
    
class FetchDepartmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = api_models.Department
        fields = '__all__'


class CreateWaveSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    lead_coach = serializers.CharField(max_length=255)
    start_date = serializers.CharField(max_length=255)
    end_date = serializers.CharField(max_length=255)


class UpdateWaveSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)
    start_date = serializers.CharField(max_length=255)
    end_date = serializers.CharField(max_length=255)
    lead_coach = serializers.CharField(max_length=255)
    
class FetchWaveSerializer(serializers.ModelSerializer):
    lead_coach = UsersSerializer()
    class Meta:
        model = api_models.Wave
        fields = '__all__'


class FetchTitleSerializer(serializers.ModelSerializer):

    class Meta:
        model = api_models.Title
        fields = '__all__'


class CreateOverseerSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    contact = serializers.CharField(max_length=255)
    title = serializers.CharField(max_length=255)


class FetchOverseerSerializer(serializers.ModelSerializer):
    title = FetchTitleSerializer()
    class Meta:
        model = api_models.Overseer
        fields = '__all__'


class CreateThematicAreaSerializer(serializers.Serializer):
    department = serializers.CharField(max_length=255)
    sector = serializers.CharField(max_length=255)
    area = serializers.CharField(max_length=500)
    results_leader = serializers.CharField(max_length=255)
    team_leader = serializers.CharField(max_length=255)
    strategic_leader = serializers.CharField(max_length=255)


class FetchThematicAreaSerializer(serializers.ModelSerializer):
    sector = FetchSectorSerializer()
    department = FetchDepartmentSerializer()
    results_leader = FetchOverseerSerializer()
    team_leader = FetchOverseerSerializer()
    strategic_leader = FetchOverseerSerializer()
    members = serializers.SerializerMethodField()

    class Meta:
        model = api_models.ThematicArea
        fields = '__all__'

    def get_members(self, obj):
        try:
            finds = api_models.TeamMembers.objects.filter(Q(thematic_area=obj))
            members = [ member.name for member in finds ]
            return members
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []


class CreateRRIGoalsSerializer(serializers.Serializer):
    wave = serializers.CharField(max_length=255)
    goal = serializers.CharField(max_length=500)
    coach = serializers.CharField(max_length=255)
    thematic_area = serializers.CharField(max_length=255)


class UpdateRRIGoalsSerializer(serializers.Serializer):
    wave = serializers.CharField(max_length=500)
    goal = serializers.CharField(max_length=500)
    coach = serializers.CharField(max_length=255)
    thematic_area = serializers.CharField(max_length=255)
    request_id = serializers.CharField(max_length=255)


class FetchRRIGoalsSerializer(serializers.ModelSerializer):
    wave = FetchWaveSerializer()
    coach = FetchOverseerSerializer()
    thematic_area = FetchThematicAreaSerializer()
    achievements = serializers.SerializerMethodField()
    class Meta:
        model = api_models.RRIGoals
        fields = '__all__'

    def get_achievements(self, obj):
        try:
            documents = api_models.Achievement.objects.filter(Q(thematic_area=obj.thematic_area))
            serializer = FetchAchievementSerializer(documents, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []


class CreateTeamMembersSerializer(serializers.Serializer):
    member = serializers.CharField(max_length=255)
    thematic_area = serializers.CharField(max_length=255)

class CreateEvidenceSerializer(serializers.Serializer):
    thematic_area_id = serializers.CharField(max_length=255)
    description = serializers.CharField(max_length=1000)
    upload_status = serializers.CharField(max_length=255)


class FetchAchievementDocumentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.AchievementDocuments
        fields = '__all__'

class FetchAchievementSerializer(serializers.ModelSerializer):
    # thematic_area = FetchThematicAreaSerializer()
    documents = serializers.SerializerMethodField()
    
    class Meta:
        model = api_models.Achievement
        fields = '__all__'
    
    def get_documents(self, obj):
        try:
            documents = api_models.AchievementDocuments.objects.filter(Q(achievement=obj))
            serializer = FetchAchievementDocumentsSerializer(documents, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []


class FetchTeamMembersSerializer(serializers.ModelSerializer):
    thematic_area = FetchThematicAreaSerializer()
    class Meta:
        model = api_models.TeamMembers
        fields = '__all__'



class CreateDepartmentSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)


class EditDepartmentSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)


class DepartmentSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)