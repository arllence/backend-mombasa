from django.db.models import  Q
from api import models as api_models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)


class FetchSectorSerializer(serializers.ModelSerializer):

    class Meta:
        model = api_models.Sector
        fields = '__all__'


class FetchDepartmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = api_models.Department
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
    department = serializers.TextField(max_length=255)
    sector = serializers.TextField(max_length=255)
    area = serializers.TextField(max_length=255)
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
    goal = serializers.TextField()
    thematic_area = serializers.CharField(max_length=255)


class FetchRRIGoalsSerializer(serializers.ModelSerializer):
    thematic_area = FetchThematicAreaSerializer()
    class Meta:
        model = api_models.RRIGoals
        fields = '__all__'


class CreateTeamMembersSerializer(serializers.Serializer):
    member = serializers.CharField(max_length=255)
    thematic_area = serializers.CharField(max_length=255)


class FetchTeamMembersSerializer(serializers.ModelSerializer):
    thematic_area = FetchThematicAreaSerializer()
    class Meta:
        model = api_models.TeamMembers
        fields = '__all__'