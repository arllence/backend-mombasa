import math
from urllib import request
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

class CreateSubSectorSerializer(serializers.Serializer):
    name = serializers.ListField()
    sector = serializers.CharField(max_length=255)

class UpdateSubSectorSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)
    sector = serializers.CharField(max_length=255)    

class FetchSubSectorSerializer(serializers.ModelSerializer):
    sector = FetchSectorSerializer()
    class Meta:
        model = api_models.SubSector
        fields = '__all__'

class CreateDirectorateSerializer(serializers.Serializer):
    name = serializers.ListField()
    sub_sector = serializers.CharField(max_length=255)

class UpdateDirectorateSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)
    sub_sector = serializers.CharField(max_length=255)    

class FetchDirectorateSerializer(serializers.ModelSerializer):
    sub_sector = FetchSubSectorSerializer()
    class Meta:
        model = api_models.Directorate
        fields = '__all__'


class UpdateDepartmentSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)
    
class FetchDepartmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = api_models.Department
        fields = '__all__'
        

class FetchProjectSubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.ProjectSubCategory
        fields = '__all__'

class CreateWaveSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    start_date = serializers.CharField(max_length=255)
    end_date = serializers.CharField(max_length=255)
    budget = serializers.CharField(max_length=255)
    type = serializers.CharField(max_length=255)
    directorate = serializers.CharField(max_length=255)
    sub_category = serializers.CharField(max_length=255)
    risks = serializers.CharField(max_length=3000)


class UpdateWaveSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)
    start_date = serializers.CharField(max_length=255)
    end_date = serializers.CharField(max_length=255)
    budget = serializers.CharField(max_length=255)
    type = serializers.CharField(max_length=255)
    sub_category = serializers.CharField(max_length=255)
    directorate = serializers.CharField(max_length=255)
    
class SlimFetchWaveSerializer(serializers.ModelSerializer):
    # lead_coach = UsersSerializer()
    directorate = FetchDirectorateSerializer()
    sub_category = FetchProjectSubCategorySerializer()
    
    class Meta:
        model = api_models.Wave
        fields = '__all__'
        

    
class FetchWaveSerializer(serializers.ModelSerializer):
    # lead_coach = UsersSerializer()
    directorate = FetchDirectorateSerializer()
    sub_category = FetchProjectSubCategorySerializer()
    sub_projects = serializers.SerializerMethodField()
    
    class Meta:
        model = api_models.Wave
        fields = '__all__'
        
    def get_sub_projects(self, obj):
        try:
            plans = api_models.Wave.objects.filter(Q(mother_id=obj.id) & Q(is_deleted=False))
            serializer = SubProjectFetchWaveSerializer(plans, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []
    
class SubProjectFetchWaveSerializer(serializers.ModelSerializer):
    sub_category = FetchProjectSubCategorySerializer()
    objectives = serializers.SerializerMethodField()
    class Meta:
        model = api_models.Wave
        fields = '__all__'

    def get_objectives(self, obj):
        try:
            objectives = api_models.RRIGoals.objects.filter(Q(wave=obj.id) & Q(is_deleted=False))
            serializer = SlimFetchRRIGoalsSerializer(objectives, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []

class SlimFetchWaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.Wave
        fields = '__all__'

class FetchTitleSerializer(serializers.ModelSerializer):

    class Meta:
        model = api_models.Title
        fields = '__all__'


class CreateOverseerSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    # contact = serializers.CharField(max_length=255)
    title = serializers.CharField(max_length=255)


class FetchOverseerSerializer(serializers.ModelSerializer):
    title = FetchTitleSerializer()
    class Meta:
        model = api_models.Overseer
        fields = '__all__'


class CreateThematicAreaSerializer(serializers.Serializer):
    department = serializers.CharField(max_length=255)
    sector = serializers.CharField(max_length=255)
    area = serializers.CharField(max_length=5000)
    project = serializers.CharField(max_length=500)


class UpdateThematicAreaSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    department = serializers.CharField(max_length=255)
    sector = serializers.CharField(max_length=255)
    area = serializers.CharField(max_length=5000)
    project = serializers.CharField(max_length=500)
    


class FetchThematicAreaSerializer(serializers.ModelSerializer):
    sector = FetchSectorSerializer()
    directorate = FetchDirectorateSerializer()
    # department = FetchDepartmentSerializer()

    class Meta:
        model = api_models.ThematicArea
        fields = '__all__'


class CreateRRIGoalsSerializer(serializers.Serializer):
    wave = serializers.CharField(max_length=255)
    goal = serializers.CharField(max_length=500)
    thematic_area = serializers.CharField(max_length=255)


class UpdateRRIGoalsSerializer(serializers.Serializer):
    wave = serializers.CharField(max_length=500)
    goal = serializers.CharField(max_length=500)
    thematic_area = serializers.CharField(max_length=255)
    request_id = serializers.CharField(max_length=255)


class SlimFetchRRIGoalsSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.RRIGoals
        fields = '__all__'

class FetchRRIGoalsSerializer(serializers.ModelSerializer):
    wave = FetchWaveSerializer()
    thematic_area = FetchThematicAreaSerializer()
    achievements = serializers.SerializerMethodField()
    workplan = serializers.SerializerMethodField()
    result_chain = serializers.SerializerMethodField()
    team_members = serializers.SerializerMethodField()
    evaluation = serializers.SerializerMethodField()
    assigned = serializers.SerializerMethodField()
    evaluation_analytics = serializers.SerializerMethodField()

    class Meta:
        model = api_models.RRIGoals
        fields = '__all__'

    def get_achievements(self, obj):
        try:
            before_documents, during_documents, after_documents = [[],[],[]]
            before_documents = api_models.Achievement.objects.filter(Q(thematic_area=obj.thematic_area) & Q(category='BEFORE'))
            if before_documents:
                before_documents = FetchAchievementSerializer(before_documents, many=True).data
            during_documents = api_models.Achievement.objects.filter(Q(thematic_area=obj.thematic_area) & Q(category='DURING'))
            if during_documents:
                during_documents = FetchAchievementSerializer(during_documents, many=True).data
            after_documents = api_models.Achievement.objects.filter(Q(thematic_area=obj.thematic_area) & Q(category='AFTER'))
            if after_documents:
                after_documents = FetchAchievementSerializer(after_documents, many=True).data

            data = {
                'before': before_documents,
                'during': during_documents,
                'after': after_documents,
            }
            return data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {}
        
    # def get_weekly_reports(self, obj):
    #     try:
    #         weekly_reports = api_models.WeeklyReports.objects.filter(Q(rri_goal=obj.id))
    #         serializer = FetchWeeklyReportSerializer(weekly_reports, many=True)
    #         return serializer.data
    #     except (ValidationError, ObjectDoesNotExist):
    #         return []
    #     except Exception as e:
    #         print(e)
    #         # logger.error(e)
    #         return []
        
    def get_workplan(self, obj):
        try:
            plans = api_models.WorkPlan.objects.filter(Q(rri_goal=obj.id) & Q(is_deleted=False))
            serializer = FetchWorkPlanSerializer(plans, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []
    
    def get_result_chain(self, obj):
        try:
            plans = api_models.ResultChain.objects.filter(Q(workplan__rri_goal=obj.id))
            serializer = FetchResultChainSerializer(plans, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []
        
    def get_evaluation(self, obj):
        try:
            evaluations = api_models.Evaluation.objects.filter(Q(rri_goal=obj.id))
            serializer = FetchEvaluationSerializer(evaluations, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []
        
    def get_evaluation_analytics(self, obj):
        try:
            evaluations = api_models.Evaluation.objects.filter(Q(rri_goal=obj.id))
            total_assignings = api_models.AssignedEvaluations.objects.filter(Q(rri_goal=obj.id)).count()
            total_score = 0
            average = 0
            average_percentage = 0
            percentages = 0

            if evaluations:
                for evaluation in evaluations:
                    total_score += evaluation.data['total']
                if total_assignings > 0:
                    average = total_score / total_assignings
                    average = round(average, 2)
                else:
                    average = total_score


            try:
                milestones = api_models.WorkPlan.objects.filter(Q(rri_goal=obj.id))
                total_milestones = len(milestones)
                
                for milestone in milestones:
                    percentages += milestone.percentage
                if percentages > 0:
                    average_percentage = math.ceil(percentages / total_milestones) 
            except Exception as e:
                print(e)

            try:
                counter = 0
                summary = 0
                goal_percentage = 0
                reports = api_models.WeeklyReports.objects.filter(Q(workplan__rri_goal=obj.id))
                for report in reports:
                    activities = report.activities
                    for activity in activities:
                        completion = activity.get('percentage_completion')
                        if not completion:
                            completion = 0
                        counter += 1
                        summary += completion
                if counter:
                    goal_percentage = math.ceil(summary / counter)
            except Exception as e:
                print(e)

            resp = {"average_score": average, "average_percentage":average_percentage, "goal_percentage":goal_percentage}
                
            return resp
        except (ValidationError, ObjectDoesNotExist):
            resp = {"average_score": 0, "average_percentage":0, "goal_percentage":0}
            return resp
        except Exception as e:
            print(e)
            # logger.error(e)
            resp = {"average_score": 0, "average_percentage":0, "goal_percentage":0}
            return resp
        
    def get_team_members(self, obj):
        try:
            finds = api_models.TeamMembers.objects.filter(Q(goal=obj.id))
            members = [ member.name for member in finds ]
            return members
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []
        
    def get_assigned(self, obj):
        try:
            # try:
            #     user_id = str(self.context["user_id"])
            #     finds = api_models.AssignedEvaluations.objects.filter(Q(rri_goal=obj.id) & Q(evaluator=user_id))
            # except Exception as e:
            #     print(e)
            #     user_id = None

            finds = api_models.AssignedEvaluations.objects.filter(Q(rri_goal=obj.id))

            members = [
                {"id":user.evaluator.id, "name":f"{user.evaluator.first_name} {user.evaluator.last_name}", "email":user.evaluator.email, "is_evaluated": user.is_evaluated}
                for user in finds
             ]
            return members
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []


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

class CreateTeamMembersSerializer(serializers.Serializer):
    member = serializers.CharField(max_length=255)
    goal = serializers.CharField(max_length=255)


class FetchTeamMembersSerializer(serializers.ModelSerializer):
    goal = FetchRRIGoalsSerializer()
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


class WWorkPlanSerializer(serializers.Serializer):
    start_date = serializers.CharField(max_length=255)
    end_date = serializers.CharField(max_length=255)
    milestone = serializers.CharField(max_length=255)
    rri_goal = serializers.CharField(max_length=255)
    budget = serializers.IntegerField()
    status = serializers.CharField(max_length=255)
    remarks = serializers.CharField(max_length=800)
    risks = serializers.CharField(max_length=800)



class UpdateWWorkPlanSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    start_date = serializers.CharField(max_length=255)
    end_date = serializers.CharField(max_length=255)
    milestone = serializers.CharField(max_length=255)
    rri_goal = serializers.CharField(max_length=255)
    budget = serializers.IntegerField()
    status = serializers.CharField(max_length=255)
    remarks = serializers.CharField(max_length=800)

class PatchWorkPlanSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    percentage = serializers.CharField(max_length=255)


class WeeklyReportSerializer(serializers.Serializer):
    # workplan = serializers.CharField(max_length=255)
    report = serializers.JSONField()


class UpdateWeeklyReportSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    workplan = serializers.CharField(max_length=255)
    activities = serializers.JSONField()


class FetchWeeklyReportSerializer(serializers.ModelSerializer):
    # workplan = FetchWorkPlanSerializer()
    class Meta:
        model = api_models.WeeklyReports
        fields = '__all__'


class FetchWorkPlanSerializer(serializers.ModelSerializer):
    weekly_reports = serializers.SerializerMethodField()
    workplan_analytics = serializers.SerializerMethodField()

    class Meta:
        model = api_models.WorkPlan
        fields = '__all__'

    
    def get_weekly_reports(self, obj):
        try:
            reports = api_models.WeeklyReports.objects.get(Q(workplan=obj))
            serializer = FetchWeeklyReportSerializer(reports, many=False)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []

    def get_workplan_analytics(self, obj):
        try:
            counter = 0
            summary = 0
            report = api_models.WeeklyReports.objects.get(Q(workplan=obj))
            activities = report.activities
            for activity in activities:
                completion = activity.get('percentage_completion')
                if not completion:
                    completion = 0
                counter += 1
                summary += completion
            goal_percentage = math.ceil(summary / counter)
            analytics = { "completion": goal_percentage }
            return analytics
        except (ValidationError, ObjectDoesNotExist):
            return { "completion": 0 }
        except Exception as e:
            print(e)



class ResultChainSerializer(serializers.Serializer):
    workplan = serializers.CharField(max_length=255)
    impact = serializers.JSONField()
    outcome = serializers.JSONField()
    output = serializers.JSONField()
    input = serializers.JSONField()
    # activities = serializers.JSONField()



class UpdateResultChainSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    workplan = serializers.CharField(max_length=255)
    impact = serializers.CharField(max_length=800)
    outcome = serializers.CharField(max_length=800)
    output = serializers.CharField(max_length=800)
    input = serializers.CharField(max_length=800)
    # activities = serializers.JSONField()



class FetchResultChainSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.ResultChain
        fields = '__all__'


class EvaluationSerializer(serializers.Serializer):
    rri_goal = serializers.CharField(max_length=255)
    data = serializers.JSONField()


class UpdateEvaluationSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    rri_goal = serializers.CharField(max_length=255)
    data = serializers.JSONField()


class FetchEvaluationSerializer(serializers.ModelSerializer):
    evaluator = UsersSerializer()
    class Meta:
        model = api_models.Evaluation
        fields = '__all__'

class ReportsFetchEvaluationSerializer(serializers.ModelSerializer):
    evaluator = UsersSerializer()
    rri_goal = FetchRRIGoalsSerializer()
    class Meta:
        model = api_models.Evaluation
        fields = '__all__'


class AssignedEvaluationsSerializer(serializers.Serializer):
    evaluator = serializers.ListField(max_length=255)


class FetchAssignedEvaluationsSerializer(serializers.ModelSerializer):
    evaluator = UsersSerializer()
    rri_goal = FetchRRIGoalsSerializer()
    class Meta:
        model = api_models.AssignedEvaluations()
        fields = '__all__'


class FetchBoroughSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.Borough
        fields = '__all__'

# sub counties 
class CreateSubCountySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    borough = serializers.CharField(max_length=255)

class UpdateSubCountySerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)
    borough = serializers.CharField(max_length=255)
    
class FetchSubCountySerializer(serializers.ModelSerializer):
    borough = FetchBoroughSerializer()
    class Meta:
        model = api_models.SubCounty
        fields = '__all__'


# wards
class CreateWardSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    sub_county = serializers.CharField(max_length=255)

class UpdateWardSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)
    sub_county = serializers.CharField(max_length=255)
    
class FetchWardSerializer(serializers.ModelSerializer):
    sub_county = FetchSubCountySerializer()
    class Meta:
        model = api_models.Ward
        fields = '__all__'


# estates
class CreateEstateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    ward = serializers.CharField(max_length=255)

class UpdateEstateSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)
    ward = serializers.CharField(max_length=255)
    
class FetchEstateSerializer(serializers.ModelSerializer):
    ward = FetchWardSerializer()
    class Meta:
        model = api_models.Estate
        fields = '__all__'