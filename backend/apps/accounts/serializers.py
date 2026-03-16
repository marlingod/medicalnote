from rest_framework import serializers
from dj_rest_auth.registration.serializers import RegisterSerializer

from apps.accounts.models import DeviceToken, Practice, User


class DoctorRegistrationSerializer(RegisterSerializer):
    username = serializers.HiddenField(default="", required=False)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    practice_name = serializers.CharField(required=True, max_length=255)
    specialty = serializers.CharField(required=False, max_length=100, default="")

    def validate_username(self, username):
        return ""

    def validate_practice_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Practice name is required.")
        return value.strip()

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data["first_name"] = self.validated_data.get("first_name", "")
        data["last_name"] = self.validated_data.get("last_name", "")
        data["practice_name"] = self.validated_data.get("practice_name", "")
        data["specialty"] = self.validated_data.get("specialty", "")
        return data

    def custom_signup(self, request, user):
        practice = Practice.objects.create(
            name=self.validated_data["practice_name"],
            subscription_tier="solo",
        )
        user.first_name = self.validated_data["first_name"]
        user.last_name = self.validated_data["last_name"]
        user.role = "doctor"
        user.practice = practice
        user.specialty = self.validated_data.get("specialty", "")
        user.save()


class UserDetailSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    practice = serializers.CharField(source="practice.id", read_only=True, default=None)
    practice_name = serializers.CharField(source="practice.name", read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "specialty",
            "license_number",
            "practice",
            "practice_name",
            "language_preference",
            "created_at",
        ]
        read_only_fields = ["id", "email", "role", "created_at"]


class PracticeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = Practice
        fields = [
            "id",
            "name",
            "address",
            "phone",
            "subscription_tier",
            "white_label_config",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ["id", "token", "platform", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]

    def validate_platform(self, value):
        if value not in ("ios", "android"):
            raise serializers.ValidationError("Platform must be 'ios' or 'android'.")
        return value


class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone",
            "language_preference",
            "email",
        ]
        read_only_fields = ["phone", "email"]
