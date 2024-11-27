import uuid
from acl.models import User, SRRSDepartment
from django.db import models
from django.conf import settings


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    department = models.ForeignKey(
        SRRSDepartment, on_delete=models.DO_NOTHING, 
        related_name='intranet_document_department')
    
    sub_department = models.ForeignKey(
        'SubDepartment', on_delete=models.DO_NOTHING, 
        related_name='intranet_document_sub_department',
        null=True, blank=True)
    
    category = models.ForeignKey(
        'SubDepartmentCategory', on_delete=models.DO_NOTHING, 
        related_name='intranet_document_category',
        null=True, blank=True)
    
    uploaded_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="document_uploaded_by"
    )

    document = models.FileField(upload_to='documents/intranet')
    title = models.CharField(max_length=500, null=True, blank=True)
    original_file_name = models.CharField(max_length=500)
    downloads = models.IntegerField(default=0)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title}"
    
    class Meta:
        db_table = u'"{}\".\"documents"'.format(settings.INTRANET)


class Qips(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="qips_created_by"
    )

    topic = models.CharField(max_length=500)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title}"
    
    class Meta:
        db_table = u'"{}\".\"qips"'.format(settings.INTRANET)

class QipsSubTopic(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    qips = models.ForeignKey(
       Qips, on_delete=models.DO_NOTHING, 
       related_name="qips_topic"
    )

    sub_topic = models.CharField(max_length=500)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sub_topic}"
    
    class Meta:
        db_table = u'"{}\".\"qips_sub_topic"'.format(settings.INTRANET)


class QipsCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    sub_topic = models.ForeignKey(
       QipsSubTopic, on_delete=models.DO_NOTHING, 
       related_name="qips_sub_topic"
    )

    category = models.CharField(max_length=500)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category}"
    
    class Meta:
        db_table = u'"{}\".\"qips_category"'.format(settings.INTRANET)   


class QipsDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    topic = models.ForeignKey(
        Qips, on_delete=models.DO_NOTHING, 
        related_name='qips_document')
    
    sub_topic = models.ForeignKey(
        QipsSubTopic, on_delete=models.DO_NOTHING, 
        related_name='qips_subtopic_document', null=True, blank=True)
    
    category = models.ForeignKey(
        QipsCategory, on_delete=models.DO_NOTHING, 
        related_name='qips_category_document', null=True, blank=True)
    
    uploaded_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="qips_document_uploaded_by"
    )

    document = models.FileField(upload_to='documents/intranet/qips')
    file_name = models.CharField(max_length=500)
    downloads = models.IntegerField(default=0)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file_name}"
    
    class Meta:
        db_table = u'"{}\".\"qips_documents"'.format(settings.INTRANET)
        

class QuickLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="link_created_by"
    )

    general_document = models.ForeignKey(
       'GeneralDocument', on_delete=models.DO_NOTHING, 
       related_name="general_document", null=True, blank=True
    )

    title = models.CharField(max_length=500)
    link = models.URLField()
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title}"
    
    class Meta:
        db_table = u'"{}\".\"quick_links"'.format(settings.INTRANET)


class SubDepartment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    department = models.ForeignKey(
       SRRSDepartment, on_delete=models.DO_NOTHING, 
       related_name="srrs_main_department"
    )

    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="sub_department_created_by"
    )

    name = models.CharField(max_length=500)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"
    
    class Meta:
        db_table = u'"{}\".\"sub_departments"'.format(settings.INTRANET)


class SubDepartmentCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    sub_department = models.ForeignKey(
       SubDepartment, on_delete=models.DO_NOTHING, 
       related_name="sub_department"
    )

    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="category_created_by"
    )

    name = models.CharField(max_length=500)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"
    
    class Meta:
        db_table = u'"{}\".\"sub_department_categories"'.format(settings.INTRANET)



class Survey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="survey_created_by"
    )

    topic = models.CharField(max_length=500)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title}"
    
    class Meta:
        db_table = u'"{}\".\"survey"'.format(settings.INTRANET)

class SurveySubTopic(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    survey = models.ForeignKey(
       Survey, on_delete=models.DO_NOTHING, 
       related_name="survey_topic"
    )

    sub_topic = models.CharField(max_length=500)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sub_topic}"
    
    class Meta:
        db_table = u'"{}\".\"survey_sub_topic"'.format(settings.INTRANET)


class SurveyCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    sub_topic = models.ForeignKey(
       SurveySubTopic, on_delete=models.DO_NOTHING, 
       related_name="survey_sub_topic",
       null=True, blank=True
    )

    category = models.CharField(max_length=500)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category}"
    
    class Meta:
        db_table = u'"{}\".\"survey_category"'.format(settings.INTRANET)  


class SurveyLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    topic = models.ForeignKey(
        Survey, on_delete=models.DO_NOTHING, 
        related_name='survey_link')
    
    sub_topic = models.ForeignKey(
        SurveySubTopic, on_delete=models.DO_NOTHING, 
        related_name='survey_subtopic_link', null=True, blank=True)
    
    category = models.ForeignKey(
        SurveyCategory, on_delete=models.DO_NOTHING, 
        related_name='survey_category_link', null=True, blank=True)
    
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="survey_link_created_by"
    )

    link = models.URLField(max_length=200)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.link}"
    
    class Meta:
        db_table = u'"{}\".\"survey_links"'.format(settings.INTRANET)


class Module(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="modules_created_by"
    )

    topic = models.CharField(max_length=500)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title}"
    
    class Meta:
        db_table = u'"{}\".\"modules"'.format(settings.INTRANET)

class ModuleSubTopic(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    module = models.ForeignKey(
       Module, on_delete=models.DO_NOTHING, 
       related_name="module_topic"
    )

    sub_topic = models.CharField(max_length=500)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sub_topic}"
    
    class Meta:
        db_table = u'"{}\".\"module_sub_topics"'.format(settings.INTRANET)


class ModuleCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    sub_topic = models.ForeignKey(
       ModuleSubTopic, on_delete=models.DO_NOTHING, 
       related_name="module_sub_topic"
    )

    category = models.CharField(max_length=500)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category}"
    
    class Meta:
        db_table = u'"{}\".\"module_categories"'.format(settings.INTRANET)  


class ModuleLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    topic = models.ForeignKey(
        Module, on_delete=models.DO_NOTHING, 
        related_name='module_link')
    
    sub_topic = models.ForeignKey(
        ModuleSubTopic, on_delete=models.DO_NOTHING, 
        related_name='module_subtopic_link', null=True, blank=True)
    
    category = models.ForeignKey(
        ModuleCategory, on_delete=models.DO_NOTHING, 
        related_name='module_category_link', null=True, blank=True)
    
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="module_link_created_by"
    )

    link = models.URLField(max_length=200)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.link}"
    
    class Meta:
        db_table = u'"{}\".\"module_links"'.format(settings.INTRANET)


# General Documents
class GeneralDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    uploaded_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="general_document_uploaded_by"
    )

    document = models.FileField(upload_to='documents/intranet')
    title = models.CharField(max_length=500)
    file_name = models.CharField(max_length=500)
    is_quick_link = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title}"
    
    class Meta:
        db_table = u'"{}\".\"general_documents"'.format(settings.INTRANET)