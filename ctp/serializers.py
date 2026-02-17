from django.db.models import  Q
from acl.models import Hods
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, SlimFetchSRRSDepartmentSerializer
from srrs.serializers import FetchOHCSerializer, FetchSubDepartmentSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from ctp import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class UpdateGeneralNameSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)

class CreateTrainingMaterialSerializer(serializers.Serializer):
    title = serializers.CharField()
    type = serializers.CharField()
    description = serializers.CharField()
    department = serializers.CharField(max_length=255)

class UpdateTrainingMaterialSerializer(serializers.Serializer):
    request_id = serializers.CharField()
    title = serializers.CharField()
    type = serializers.CharField()
    category = serializers.CharField()
    description = serializers.CharField()
    department = serializers.CharField(max_length=255)

class SlimFetchTrainingMaterialSerializer(serializers.ModelSerializer):
    department = SlimFetchSRRSDepartmentSerializer()
    created_by = SlimUsersSerializer()
    class Meta:
        model = models.TrainingMaterial
        fields = '__all__'

class SlimFetchDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Document
        fields = '__all__'

class FetchTrainingMaterialSerializer(serializers.ModelSerializer):
    department = SlimFetchSRRSDepartmentSerializer()
    documents = serializers.SerializerMethodField()
    assignment = serializers.SerializerMethodField()
    test = serializers.SerializerMethodField()
    can_add_test = serializers.SerializerMethodField()
    created_by = SlimUsersSerializer()
    
    class Meta:
        model = models.TrainingMaterial
        fields = '__all__'

    def get_documents(self, obj):
        try:
            request = models.Document.objects.filter(training=obj, is_deleted=False)
            serializer = SlimFetchDocumentSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return [] 
        
    def get_assignment(self, obj):
        try:
            user_id = str(self.context["user_id"])
            request = models.TrainingAssignment.objects.get(training=obj, user=user_id, is_deleted=False)
            serializer = SlimFetchTrainingAssignmentSerializer(request, many=False)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return None
        except Exception as e:
            print(e)
            # logger.error(e)
            return None 
        
    def get_can_add_test(self, obj):
        try:
            user_id = str(self.context["user_id"])
            roles = get_user_roles(user_id)
            # is_department_hod = Hods.objects.filter(hod_id=user_id,department=obj.department).exists()
            is_department_hod = False
            if "SUPERUSER" in roles or is_department_hod or str(obj.created_by.id) == user_id:
                return True
            return False
        except (ValidationError, ObjectDoesNotExist):
            return False
        except Exception as e:
            print(e)
            # logger.error(e)
            return False 
        
    def get_test(self, obj):
        user_id = str(self.context["user_id"])

        try:
            test = models.Test.objects.get(training=obj)
        except models.Test.DoesNotExist:
            return {
                "id": "",
                "is_completed": False,
                "percentage": None,
                "passed": None,
                "pass_mark": None,
                "attempt_date": None
            }

        attempt = (
            models.Attempt.objects
            .filter(
                learner_id=user_id,
                test=test,
                completed_at__isnull=False
            )
            .only("passed", "percentage")   # 🔥 important
            .first()
        )

        return {
            "id": str(test.id),
            "is_completed": bool(attempt),
            "passed": attempt.passed if attempt else None,
            "percentage": attempt.percentage if attempt else None,
            "pass_mark": str(test.pass_mark),
            "attempt_date": str(attempt.completed_at) if attempt else None
        }

        
class UploadFileSerializer(serializers.Serializer):
    training_id = serializers.CharField()

# TrainingAssignment

class CreateTrainingAssignmentSerializer(serializers.Serializer):
    assign_to = serializers.CharField()
    training = serializers.CharField()

class UpdateTrainingAssignmentSerializer(serializers.Serializer):
    request_id = serializers.CharField()
    user = serializers.CharField()
    training = serializers.CharField()

class SlimFetchTrainingAssignmentSerializer(serializers.ModelSerializer):
    assigned_by = SlimUsersSerializer()
    class Meta:
        model = models.TrainingAssignment
        fields = '__all__'

class FetchTrainingAssignmentSerializer(serializers.ModelSerializer):
    training = SlimFetchTrainingMaterialSerializer()
    # documents = serializers.SerializerMethodField()
    user = SlimUsersSerializer()
    assigned_by = SlimUsersSerializer()
    
    class Meta:
        model = models.TrainingAssignment
        fields = '__all__'
        
# PlatformAdmin

class PlatformAdminSerializer(serializers.Serializer):
    admin = serializers.CharField(max_length=500)

class UpdatePlatformAdminSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    admin = serializers.CharField(max_length=500)

class FetchPlatformAdminSerializer(serializers.ModelSerializer):
    created_by = SlimUsersSerializer()
    admin = UsersSerializer()
    class Meta:
        model = models.PlatformAdmin
        fields = '__all__'





# TEST FUNC

# Option (Trainer View)
class TrainerOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Option
        fields = ["id", "text", "is_correct"]

# Question (Trainer)
class TrainerQuestionSerializer(serializers.ModelSerializer):
    options = TrainerOptionSerializer(many=True)

    class Meta:
        model = models.Question
        fields = ["id", "text", "marks", "options"]

    def create(self, validated_data):
        options_data = validated_data.pop("options")
        question = models.Question.objects.create(**validated_data)

        correct_count = 0
        for option in options_data:
            if option.get("is_correct"):
                correct_count += 1
            models.Option.objects.create(question=question, **option)

        if correct_count != 1:
            raise serializers.ValidationError(
                "Each question must have exactly one correct option."
            )

        return question
    
# Test (Trainer)
class TrainerTestSerializer(serializers.ModelSerializer):
    questions = TrainerQuestionSerializer(many=True, read_only=True)
    class Meta:
        model = models.Test
        fields = [
            "id",
            "training",
            "pass_mark",
            "duration_minutes",
            "is_active",
            "questions",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    # def create(self, validated_data):
    #     return models.Test.objects.create(
    #         trainer=self.context["request"].user,
    #         **validated_data
    #     )

# 3️⃣ Learner Serializers (Test Taking)
# Option (Learner – NO is_correct)
class LearnerOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Option
        fields = ["id", "text"]

# Question (Learner)
class LearnerQuestionSerializer(serializers.ModelSerializer):
    options = LearnerOptionSerializer(many=True)

    class Meta:
        model = models.Question
        fields = ["id", "text", "marks", "options"]

# Test Start Serializer
class TestStartSerializer(serializers.ModelSerializer):
    questions = LearnerQuestionSerializer(many=True)

    class Meta:
        model = models.Test
        fields = ["id", "training", "duration_minutes", "questions"]

# 4️⃣ Attempt & Answer Serializers
# Answer Submission
class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Answer
        fields = ["question", "selected_option"]

    
# Attempt Result Serializer
class AttemptResultSerializer(serializers.ModelSerializer):
    test_title = serializers.CharField(source="test.title", read_only=True)

    class Meta:
        model = models.Attempt
        fields = [
            "id",
            "test_title",
            "score",
            "percentage",
            "passed",
            "completed_at",
        ]

# 5️⃣ Certificate Serializers 🎓
# Certificate List (Learner)
class CertificateSerializer(serializers.ModelSerializer):
    test_title = serializers.CharField(
        source="attempt.test.title", read_only=True
    )

    class Meta:
        model = models.Certificate
        fields = [
            "id",
            "certificate_number",
            "test_title",
            "issued_at",
            "pdf",
        ]

# Certificate Verification (Public)
class CertificateVerifySerializer(serializers.ModelSerializer):
    learner = serializers.CharField(
        source="attempt.learner.email", read_only=True
    )
    test = serializers.CharField(
        source="attempt.test.title", read_only=True
    )

    class Meta:
        model = models.Certificate
        fields = ["certificate_number", "learner", "test", "issued_at"]