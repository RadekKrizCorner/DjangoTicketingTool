"""Serializers for account API endpoints."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


def normalize_email_input(email: str) -> str:
    """Normalize an email value received by the API layer."""
    return get_user_model().objects.normalize_email(email)


class UserOutputSerializer(serializers.Serializer):
    """Serialize minimal user output."""

    id = serializers.IntegerField()
    email = serializers.EmailField()
    display_name = serializers.CharField()


class UserEnvelopeSerializer(serializers.Serializer):
    """Serialize a user data envelope."""

    data = UserOutputSerializer()


class PaginationOutputSerializer(serializers.Serializer):
    """Serialize pagination metadata."""

    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)


class PaginationMetaSerializer(serializers.Serializer):
    """Serialize response metadata."""

    pagination = PaginationOutputSerializer()


class UserSearchPaginatedEnvelopeSerializer(serializers.Serializer):
    """Serialize a paginated user search data envelope."""

    data = UserOutputSerializer(many=True)
    meta = PaginationMetaSerializer()


class RegisterInputSerializer(serializers.Serializer):
    """Validate user registration input."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)
    display_name = serializers.CharField(max_length=255)

    def validate_email(self, value: str) -> str:
        """Normalize the registration email address."""
        return normalize_email_input(value)

    def validate(self, attrs: dict) -> dict:
        """Validate matching registration passwords."""
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Validate email credentials and return JWT token pairs."""

    def validate(self, attrs: dict) -> dict:
        """Normalize email before validating credentials."""
        email = attrs.get(self.username_field)
        if email is not None:
            attrs[self.username_field] = normalize_email_input(email)
        return super().validate(attrs)


class TokenOutputSerializer(serializers.Serializer):
    """Serialize JWT token output."""

    access = serializers.CharField()
    refresh = serializers.CharField()


class TokenEnvelopeSerializer(serializers.Serializer):
    """Serialize a JWT token data envelope."""

    data = TokenOutputSerializer()


class EmptyDataEnvelopeSerializer(serializers.Serializer):
    """Serialize an empty data envelope."""

    data = serializers.DictField()


class LogoutInputSerializer(serializers.Serializer):
    """Validate logout input."""

    refresh = serializers.CharField()


class StatusOutputSerializer(serializers.Serializer):
    """Serialize a status output payload."""

    status = serializers.CharField()


class StatusEnvelopeSerializer(serializers.Serializer):
    """Serialize a status data envelope."""

    data = StatusOutputSerializer()


class ProfileOutputSerializer(serializers.Serializer):
    """Serialize user profile output."""

    timezone = serializers.CharField()


class ProfileEnvelopeSerializer(serializers.Serializer):
    """Serialize a user profile data envelope."""

    data = ProfileOutputSerializer()


class ProfileUpdateInputSerializer(serializers.Serializer):
    """Validate profile update input."""

    timezone = serializers.CharField(max_length=64)

    def validate_timezone(self, value: str) -> str:
        """Validate the timezone name."""
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise serializers.ValidationError("Unknown timezone.") from exc
        return value


class PasswordChangeInputSerializer(serializers.Serializer):
    """Validate password change input."""

    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs: dict) -> dict:
        """Validate matching new passwords."""
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})
        return attrs


class PasswordResetRequestInputSerializer(serializers.Serializer):
    """Validate password reset request input."""

    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        """Normalize the password reset email address."""
        return normalize_email_input(value)


class PasswordResetConfirmInputSerializer(serializers.Serializer):
    """Validate password reset confirmation input."""

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs: dict) -> dict:
        """Validate matching password reset passwords."""
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})
        return attrs
