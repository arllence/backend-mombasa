from tracemalloc import start
import uuid
from acl.models import User
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Borough(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "boroughs"


class SubCounty(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    borough = models.ForeignKey(Borough, on_delete=models.CASCADE, related_name='subcounties')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "sub_counties"


class Ward(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    sub_county = models.ForeignKey(SubCounty, on_delete=models.DO_NOTHING, related_name='wards')
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
    class Meta:
        db_table = "wards"


class Estate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    ward = models.ForeignKey(Ward, on_delete=models.DO_NOTHING, related_name='estates')

    def __str__(self):
        return self.name
    
    class Meta:
        db_table = "estates"


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "departments"

class ProjectSubCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "project_sub_categories"

class Sector(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    date_created = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "sectors"

class SubSector(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    date_created = models.DateTimeField(auto_now_add=True)
    sector = models.ForeignKey(
        Sector, related_name="sector", on_delete=models.DO_NOTHING
    )
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "sub_sectors"

class Directorate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    date_created = models.DateTimeField(auto_now_add=True)
    sub_sector = models.ForeignKey(
        SubSector, related_name="sub_sector", on_delete=models.DO_NOTHING
    )
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "directorates"
        

class Title(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "Titles"


class Overseer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    contact = models.CharField(max_length=50)
    title = models.ForeignKey(
        Title, related_name="overseer_title", on_delete=models.DO_NOTHING
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "overseers"

class Wave(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    budget = models.IntegerField(default=0)
    type = models.CharField(max_length=255, default="MAIN")
    standalone = models.CharField(max_length=255, null=True, blank=True)
    mother_id = models.CharField(max_length=255, null=True, blank=True)
    location = models.JSONField(null=True, blank=True)
    members = models.JSONField(null=True, blank=True)
    risks = models.TextField(null=True, blank=True)
    results_leaders = models.JSONField(null=True, blank=True)
    technical_leaders = models.JSONField(null=True, blank=True)
    strategic_leaders = models.JSONField(null=True, blank=True)
    directorate = models.ForeignKey(
        Directorate, related_name="wave_directorate", on_delete=models.DO_NOTHING, null=True, blank=True
    )
    sub_category = models.ForeignKey(
        ProjectSubCategory, related_name="wave_sub_category", on_delete=models.DO_NOTHING, null=True, blank=True
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "waves"

class ThematicArea(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    area = models.TextField()
    sector = models.ForeignKey(
        Sector, related_name="thematic_area_sector", on_delete=models.DO_NOTHING
    )
    project = models.ForeignKey(
        Wave, related_name="goal_project", on_delete=models.DO_NOTHING, null=True, blank=True
    )
    directorate = models.ForeignKey(
        Directorate, related_name="thematic_area_directorate", on_delete=models.DO_NOTHING, null=True, blank=True
    )
    is_deleted = models.BooleanField(default=False)

    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.area

    class Meta:
        db_table = "thematic_areas"


class RRIGoals(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    goal = models.TextField()
    thematic_area = models.ForeignKey(
        ThematicArea, related_name="thematic_area", on_delete=models.DO_NOTHING
    )
    # coach = models.ForeignKey(
    #     Overseer, related_name="coach", on_delete=models.DO_NOTHING,
    #     null=True, blank=True
    # )
    wave = models.ForeignKey(
        Wave, related_name="wave", on_delete=models.DO_NOTHING,
        null=True, blank=True
    )
    creator = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, related_name="goal_creator",
       null=True, blank=True
    )
    results_leaders = models.JSONField(null=True, blank=True)
    technical_leaders = models.JSONField(null=True, blank=True)
    strategic_leaders = models.JSONField(null=True, blank=True)
    # results_leader = models.ForeignKey(
    #     Overseer, related_name="results_leader", on_delete=models.DO_NOTHING,
    #     null=True, blank=True
    # )
    # team_leader = models.ForeignKey(
    #     Overseer, related_name="team_leader", on_delete=models.DO_NOTHING,
    #     null=True, blank=True
    # )
    # strategic_leader = models.ForeignKey(
    #     Overseer, related_name="strategic_leader", on_delete=models.DO_NOTHING,
    #     null=True, blank=True
    # )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.goal

    class Meta:
        db_table = "rri_goals"


class TeamMembers(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    goal = models.ForeignKey(
        RRIGoals, related_name="member_goal", on_delete=models.DO_NOTHING,
        null=True, blank=True
    )
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "team_members"


class Achievement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, related_name="achievement_creator"
    )
    thematic_area = models.ForeignKey(
       ThematicArea, on_delete=models.DO_NOTHING, related_name="achievement_thematic_area"
    )
    description = models.TextField()
    category = models.CharField(max_length=50, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "achievements"

    def __str__(self):
        return str(self.description)
    
    
class AchievementDocuments(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    achievement = models.ForeignKey(
       Achievement, on_delete=models.DO_NOTHING, related_name="achievement_creator"
    )
    document = models.FileField(upload_to='county47_documents')
    original_file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50,default='FILE')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "achievement_documents"

    def __str__(self):
        return str(self.achievement)
    

class WorkPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, related_name="work_plan_creator"
    )
    rri_goal = models.ForeignKey(
       RRIGoals, on_delete=models.DO_NOTHING, related_name="work_plan_rri_goal"
    )
    person_incharge = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, related_name="work_plan_person_incharge",
       null=True, blank=True
    )
    location = models.JSONField(null=True, blank=True)
    milestone = models.CharField(max_length=500)
    steps = models.JSONField()
    collaborators = models.JSONField(null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    budget = models.IntegerField()
    status = models.CharField(max_length=50)
    remarks = models.TextField()
    risks = models.TextField(null=True, blank=True)
    percentage = models.IntegerField(validators=[MinValueValidator(0),
                                            MaxValueValidator(100)], default=0)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workplans"

    def __str__(self):
        return str(self.milestone)
    

class WeeklyReports(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, related_name="weekly_report_creator"
    )
    workplan = models.ForeignKey(
       WorkPlan, on_delete=models.DO_NOTHING, related_name="weekly_report_workplan", 
       null=True, blank=True
    )
    activities = models.JSONField()
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "weekly_reports"

    def __str__(self):
        return str(self.workplan.milestone)
    

class ResultChain(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, related_name="result_chain_creator"
    )

    workplan = models.ForeignKey(
       WorkPlan, on_delete=models.DO_NOTHING, related_name="result_chain_workplan",
       null=True, blank=True
    )
    
    activities = models.JSONField(null=True, blank=True)
    input = models.JSONField()
    output = models.JSONField()
    outcome = models.JSONField()
    impact = models.JSONField()
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "result_chain"

    def __str__(self):
        return str(self.milestone)
    


class Evaluation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evaluator = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, related_name="evaluator"
    )
    rri_goal = models.ForeignKey(
       RRIGoals, on_delete=models.DO_NOTHING, related_name="evaluated_rri_goal"
    )
    
    data = models.JSONField()
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "evaluation"

    def __str__(self):
        return str(self.rri_goal.goal)
    

class AssignedEvaluations(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evaluator = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, related_name="assigned_evaluator"
    )
    rri_goal = models.ForeignKey(
       RRIGoals, on_delete=models.DO_NOTHING, related_name="assigned_rri_goal"
    )
    is_evaluated = models.BooleanField(default=False)
    
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "assigned_evaluations"

    def __str__(self):
        return f"{str(self.evaluator.first_name)} {str(self.evaluator.last_name)}" 
    

