from tracemalloc import start
import uuid
from acl.models import User
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Wave(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    budget = models.IntegerField(default=0)
    lead_coach = models.ForeignKey(
        User, related_name="wave_lead_coach", on_delete=models.DO_NOTHING, null=True, blank=True
    )
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "waves"


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "departments"


class Sector(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "sectors"
        

class Title(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
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
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "overseers"


class ThematicArea(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    area = models.TextField()
    sector = models.ForeignKey(
        Sector, related_name="thematic_area_sector", on_delete=models.DO_NOTHING
    )
    department = models.ForeignKey(
        Department, related_name="thematic_area_department", on_delete=models.DO_NOTHING
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
    coach = models.ForeignKey(
        Overseer, related_name="coach", on_delete=models.DO_NOTHING,
        null=True, blank=True
    )
    wave = models.ForeignKey(
        Wave, related_name="wave", on_delete=models.DO_NOTHING,
        null=True, blank=True
    )
    results_leader = models.ForeignKey(
        Overseer, related_name="results_leader", on_delete=models.DO_NOTHING,
        null=True, blank=True
    )
    team_leader = models.ForeignKey(
        Overseer, related_name="team_leader", on_delete=models.DO_NOTHING,
        null=True, blank=True
    )
    strategic_leader = models.ForeignKey(
        Overseer, related_name="strategic_leader", on_delete=models.DO_NOTHING,
        null=True, blank=True
    )
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
    rri_goal = models.ForeignKey(
       RRIGoals, on_delete=models.DO_NOTHING, related_name="result_chain_rri_goal"
    )
    
    activities = models.JSONField()
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
    

class Borough(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "boroughs"


class SubCounty(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    borough = models.ForeignKey(Borough, on_delete=models.CASCADE, related_name='subcounties')
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "sub_counties"


class Ward(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    sub_county = models.ForeignKey(SubCounty, on_delete=models.DO_NOTHING, related_name='wards')

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