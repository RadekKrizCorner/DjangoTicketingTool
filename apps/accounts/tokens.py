"""Account token helpers."""

from django.contrib.auth.tokens import PasswordResetTokenGenerator

password_reset_token_generator = PasswordResetTokenGenerator()
