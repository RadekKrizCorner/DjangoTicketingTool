"""Project domain models."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import AuditSoftDeleteModel


class Project(AuditSoftDeleteModel):
    """Represent a project."""

    class Visibility(models.TextChoices):
        """List project visibility choices."""

        PRIVATE = "private", "Private"
        PUBLIC = "public", "Public"

    class State(models.TextChoices):
        """List project lifecycle state choices."""

        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"

    class PublicCommentPolicy(models.TextChoices):
        """List public project comment policy choices."""

        MEMBERS_ONLY = "members_only", "Members only"
        AUTHENTICATED_USERS = "authenticated_users", "Authenticated users"

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_projects",
    )
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.ACTIVE,
    )
    public_comment_policy = models.CharField(
        max_length=40,
        choices=PublicCommentPolicy.choices,
        default=PublicCommentPolicy.MEMBERS_ONLY,
    )
    publish_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    close_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Configure project ordering."""

        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["visibility", "state", "-created_at"],
                name="project_vis_state_created_idx",
            ),
            models.Index(fields=["owner", "-created_at"], name="project_owner_created_idx"),
        ]

    def __str__(self) -> str:
        """Return the project name."""
        return self.name

    def clean(self) -> None:
        """Validate that project owner matches active owner membership."""
        super().clean()
        if not self.pk or self.deleted_at:
            return

        owner_membership = self.memberships.filter(
            role=ProjectMembership.Role.OWNER,
            deleted_at__isnull=True,
        ).first()
        if owner_membership is None:
            raise ValidationError({"owner": "Project must have an active owner membership."})
        if owner_membership.user_id != self.owner_id:
            raise ValidationError(
                {"owner": "Project owner must match the active owner membership."}
            )


class ProjectMembership(AuditSoftDeleteModel):
    """Represent a user's role in a project."""

    class Role(models.TextChoices):
        """List project membership role choices."""

        OWNER = "owner", "Owner"
        MANAGER = "manager", "Manager"
        MEMBER = "member", "Member"
        VIEWER = "viewer", "Viewer"

    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="project_memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices)

    class Meta:
        """Configure membership ordering and active-row constraints."""

        ordering = ["project_id", "user_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"],
                condition=models.Q(deleted_at__isnull=True),
                name="projects_active_membership_project_user_uniq",
            ),
            models.UniqueConstraint(
                fields=["project"],
                condition=models.Q(role="owner", deleted_at__isnull=True),
                name="projects_one_active_owner_membership_uniq",
            ),
        ]

    def __str__(self) -> str:
        """Return a readable membership label."""
        return f"{self.project_id}:{self.user_id}:{self.role}"

    def clean(self) -> None:
        """Validate owner membership consistency."""
        super().clean()
        if self.deleted_at:
            return

        errors = {}
        self._validate_owner_membership_user(errors)
        self._validate_existing_owner_membership_change(errors)
        if errors:
            raise ValidationError(errors)

    def _validate_owner_membership_user(self, errors: dict) -> None:
        """Validate an owner membership user matches the project owner."""
        if self.role != self.Role.OWNER or not self.project_id or not self.user_id:
            return
        if self.project.owner_id != self.user_id:
            errors["user"] = "Owner membership user must match project owner."

    def _validate_existing_owner_membership_change(self, errors: dict) -> None:
        """Validate an active owner membership is not reassigned in admin forms."""
        if not self.pk:
            return

        current_membership = (
            type(self).objects.filter(pk=self.pk)
            .only("project_id", "user_id", "role", "deleted_at")
            .first()
        )
        if (
            current_membership is None
            or current_membership.deleted_at is not None
            or current_membership.role != self.Role.OWNER
        ):
            return

        if self.project_id != current_membership.project_id:
            errors["project"] = "Active owner membership project cannot be changed."
        if self.user_id != current_membership.user_id:
            errors["user"] = "Active owner membership user cannot be changed."
        if self.role != self.Role.OWNER:
            errors["role"] = "Active owner membership role cannot be changed."
