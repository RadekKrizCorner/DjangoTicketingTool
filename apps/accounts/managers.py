"""Account model managers."""

from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Manage email-based users."""

    def normalize_email(self, email: str | None) -> str:
        """Return a stripped lowercase email address."""
        if email is None:
            return ""
        return super().normalize_email(email.strip()).lower()

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        """Create a regular user with an email and password."""
        normalized_email = self.normalize_email(email)
        if not normalized_email:
            raise ValueError("Users must have an email address.")

        user = self.model(email=normalized_email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        """Create a superuser with staff and superuser permissions."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email=email, password=password, **extra_fields)

    def get_by_natural_key(self, email: str):
        """Return a user by normalized email for Django authentication."""
        return self.get(email=self.normalize_email(email))
