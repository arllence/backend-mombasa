from tracemalloc import start
import uuid
from acl.models import User
from django.db import models


class Wave(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
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
    

class WeeklyReports(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, related_name="weekly_report_creator"
    )
    rri_goal = models.ForeignKey(
       RRIGoals, on_delete=models.DO_NOTHING, related_name="weekly_report_rri_goal", 
       null=True, blank=True
    )
    milestone = models.CharField(max_length=50)
    steps = models.JSONField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "weekly_reports"

    def __str__(self):
        return str(self.milestone)
    

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
    milestone = models.CharField(max_length=50)
    steps = models.JSONField()
    start_date = models.DateField()
    end_date = models.DateField()
    budget = models.IntegerField()
    status = models.CharField(max_length=50)
    remarks = models.TextField()
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workplans"

    def __str__(self):
        return str(self.milestone)
    

class ResultChain(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, related_name="result_chain_creator"
    )
    rri_goal = models.ForeignKey(
       RRIGoals, on_delete=models.DO_NOTHING, related_name="result_chain_rri_goal"
    )
    
    activities = models.JSONField()
    input = models.TextField()
    output = models.TextField()
    outcome = models.TextField()
    impact = models.TextField()
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "result_chain"

    def __str__(self):
        return str(self.milestone)