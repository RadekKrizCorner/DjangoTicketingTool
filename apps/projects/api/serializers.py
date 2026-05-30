"""Serializers for project API endpoints."""

import re
from http import HTTPStatus
from typing import Any

from rest_framework import serializers

from apps.common.errors import DomainError
from apps.projects.models import Project, ProjectMembership

TIMEZONE_SUFFIX_RE = re.compile(r"(Z|[+-]\d{2}:\d{2})$")


class AwareDateTimeField(serializers.DateTimeField):
    """Parse datetimes while requiring an explicit timezone suffix."""

    def to_internal_value(self, value: Any):
        """Return a parsed aware datetime or raise a schedule error."""
        if isinstance(value, str) and not TIMEZONE_SUFFIX_RE.search(value.strip()):
            raise DomainError(
                code="invalid_schedule",
                detail="Timestamp must include timezone information.",
                status_code=HTTPStatus.BAD_REQUEST,
            )
        return super().to_internal_value(value)


class ProjectPaginationOutputSerializer(serializers.Serializer):
    """Serialize pagination metadata."""

    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)


class ProjectPaginationMetaSerializer(serializers.Serializer):
    """Serialize response metadata."""

    pagination = ProjectPaginationOutputSerializer()


class ProjectOutputSerializer(serializers.Serializer):
    """Serialize project output."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    owner_id = serializers.IntegerField()
    visibility = serializers.ChoiceField(choices=Project.Visibility.choices)
    state = serializers.ChoiceField(choices=Project.State.choices)
    public_comment_policy = serializers.ChoiceField(choices=Project.PublicCommentPolicy.choices)
    publish_at = serializers.DateTimeField(allow_null=True)
    published_at = serializers.DateTimeField(allow_null=True)
    close_at = serializers.DateTimeField(allow_null=True)
    closed_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ProjectEnvelopeSerializer(serializers.Serializer):
    """Serialize a project data envelope."""

    data = ProjectOutputSerializer()


class ProjectPaginatedEnvelopeSerializer(serializers.Serializer):
    """Serialize a paginated project data envelope."""

    data = ProjectOutputSerializer(many=True)
    meta = ProjectPaginationMetaSerializer()


class ProjectCreateInputSerializer(serializers.Serializer):
    """Validate project creation input."""

    name = serializers.CharField(max_length=200)
    description = serializers.CharField(allow_blank=True, required=False, default="")
    visibility = serializers.ChoiceField(
        choices=Project.Visibility.choices,
        required=False,
        default=Project.Visibility.PRIVATE,
    )
    public_comment_policy = serializers.ChoiceField(
        choices=Project.PublicCommentPolicy.choices,
        required=False,
        default=Project.PublicCommentPolicy.MEMBERS_ONLY,
    )


class ProjectUpdateInputSerializer(serializers.Serializer):
    """Validate project update input."""

    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(allow_blank=True, required=False)
    visibility = serializers.ChoiceField(choices=Project.Visibility.choices, required=False)
    public_comment_policy = serializers.ChoiceField(
        choices=Project.PublicCommentPolicy.choices,
        required=False,
    )


class ProjectMembershipOutputSerializer(serializers.Serializer):
    """Serialize project membership output."""

    id = serializers.IntegerField()
    project_id = serializers.IntegerField()
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=ProjectMembership.Role.choices)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ProjectMembershipEnvelopeSerializer(serializers.Serializer):
    """Serialize a project membership data envelope."""

    data = ProjectMembershipOutputSerializer()


class ProjectMembershipPaginatedEnvelopeSerializer(serializers.Serializer):
    """Serialize a paginated project membership envelope."""

    data = ProjectMembershipOutputSerializer(many=True)
    meta = ProjectPaginationMetaSerializer()


class ProjectMembershipInputSerializer(serializers.Serializer):
    """Validate project membership creation input."""

    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=ProjectMembership.Role.choices)


class ProjectMembershipUpdateInputSerializer(serializers.Serializer):
    """Validate project membership update input."""

    role = serializers.ChoiceField(choices=ProjectMembership.Role.choices)


class OwnershipTransferInputSerializer(serializers.Serializer):
    """Validate ownership transfer input."""

    new_owner_id = serializers.IntegerField()


class PublishScheduleInputSerializer(serializers.Serializer):
    """Validate publish schedule input."""

    publish_at = AwareDateTimeField()


class CloseScheduleInputSerializer(serializers.Serializer):
    """Validate close schedule input."""

    close_at = AwareDateTimeField()


class AuditLogOutputSerializer(serializers.Serializer):
    """Serialize audit log output."""

    id = serializers.IntegerField()
    actor_id = serializers.IntegerField(allow_null=True)
    action = serializers.CharField()
    entity_type = serializers.CharField()
    entity_id = serializers.IntegerField()
    project_id = serializers.IntegerField(allow_null=True)
    before = serializers.DictField()
    after = serializers.DictField()
    metadata = serializers.DictField()
    ip_address = serializers.IPAddressField(allow_null=True)
    user_agent = serializers.CharField(allow_blank=True)
    idempotency_key = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()


class AuditLogPaginatedEnvelopeSerializer(serializers.Serializer):
    """Serialize a paginated audit log envelope."""

    data = AuditLogOutputSerializer(many=True)
    meta = ProjectPaginationMetaSerializer()
