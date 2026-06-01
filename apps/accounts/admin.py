"""Admin registrations for account models."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import ExternalIdentity, PersonalAccessToken, User, UserProfile


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Admin configuration for email-based users."""

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("display_name",)}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "display_name", "password1", "password2"),
            },
        ),
    )
    list_display = ("email", "display_name", "is_staff", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    ordering = ("email",)
    search_fields = ("email", "display_name")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for user profiles."""

    list_display = ("user", "timezone")
    search_fields = ("user__email", "user__display_name", "timezone")


@admin.register(ExternalIdentity)
class ExternalIdentityAdmin(admin.ModelAdmin):
    """Admin configuration for external identities."""

    list_display = ("provider", "provider_subject", "user", "email_at_link_time")
    list_filter = ("provider",)
    search_fields = ("provider", "provider_subject", "email_at_link_time", "user__email")


@admin.register(PersonalAccessToken)
class PersonalAccessTokenAdmin(admin.ModelAdmin):
    """Admin configuration for personal access tokens."""

    list_display = ("name", "user", "token_prefix", "expires_at", "revoked_at", "last_used_at")
    list_filter = ("revoked_at", "expires_at", "created_at")
    readonly_fields = (
        "token_prefix",
        "token_hash",
        "created_at",
        "updated_at",
        "last_used_at",
    )
    search_fields = ("name", "user__email", "token_prefix")
