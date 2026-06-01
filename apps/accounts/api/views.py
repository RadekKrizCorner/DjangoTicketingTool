"""Views for account API endpoints."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from apps.accounts import selectors, services
from apps.accounts.api.serializers import (
    EmailTokenObtainPairSerializer,
    EmptyDataEnvelopeSerializer,
    LogoutInputSerializer,
    PasswordChangeInputSerializer,
    PasswordResetConfirmInputSerializer,
    PasswordResetRequestInputSerializer,
    PersonalAccessTokenCreateEnvelopeSerializer,
    PersonalAccessTokenCreateInputSerializer,
    PersonalAccessTokenListEnvelopeSerializer,
    PersonalAccessTokenOutputSerializer,
    ProfileEnvelopeSerializer,
    ProfileOutputSerializer,
    ProfileUpdateInputSerializer,
    RegisterInputSerializer,
    StatusEnvelopeSerializer,
    TokenEnvelopeSerializer,
    UserEnvelopeSerializer,
    UserOutputSerializer,
    UserSearchPaginatedEnvelopeSerializer,
)
from apps.api.pagination import StandardPageNumberPagination
from apps.api.responses import success_response


class RegisterView(APIView):
    """Register local users."""

    authentication_classes: tuple = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        request=RegisterInputSerializer,
        responses={201: UserEnvelopeSerializer},
    )
    def post(self, request: Request) -> Response:
        """Register a user and return minimal user data."""
        serializer = RegisterInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.register_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            display_name=serializer.validated_data["display_name"],
        )
        return success_response(
            UserOutputSerializer(user).data,
            status_code=status.HTTP_201_CREATED,
        )


class WrappedTokenObtainPairView(TokenObtainPairView):
    """Return JWT token pairs in the standard data envelope."""

    authentication_classes: tuple = ()
    permission_classes = (AllowAny,)
    serializer_class = EmailTokenObtainPairSerializer
    throttle_scope = "login"

    @extend_schema(
        request=EmailTokenObtainPairSerializer,
        responses={200: TokenEnvelopeSerializer},
    )
    def post(self, request: Request, *args, **kwargs) -> Response:
        """Authenticate a user and return a wrapped token pair."""
        response = super().post(request, *args, **kwargs)
        response.data = {"data": response.data}
        return response


class WrappedTokenRefreshView(TokenRefreshView):
    """Refresh JWT tokens in the standard data envelope."""

    authentication_classes: tuple = ()
    permission_classes = (AllowAny,)

    @extend_schema(responses={200: TokenEnvelopeSerializer})
    def post(self, request: Request, *args, **kwargs) -> Response:
        """Refresh a token and return wrapped token data."""
        response = super().post(request, *args, **kwargs)
        response.data = {"data": response.data}
        return response


class WrappedTokenVerifyView(TokenVerifyView):
    """Verify JWT tokens in the standard data envelope."""

    authentication_classes: tuple = ()
    permission_classes = (AllowAny,)

    @extend_schema(responses={200: EmptyDataEnvelopeSerializer})
    def post(self, request: Request, *args, **kwargs) -> Response:
        """Verify a token and return an empty data envelope."""
        response = super().post(request, *args, **kwargs)
        response.data = {"data": response.data}
        return response


class LogoutView(APIView):
    """Log out users by blacklisting refresh tokens."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        request=LogoutInputSerializer,
        responses={200: StatusEnvelopeSerializer},
    )
    def post(self, request: Request) -> Response:
        """Blacklist the submitted refresh token."""
        serializer = LogoutInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.logout_refresh_token(refresh=serializer.validated_data["refresh"])
        return success_response({"status": "logged_out"})


class MeView(APIView):
    """Return the authenticated user."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={200: UserEnvelopeSerializer})
    def get(self, request: Request) -> Response:
        """Return minimal data for the authenticated user."""
        return success_response(UserOutputSerializer(request.user).data)


class ProfileView(APIView):
    """Read and update the authenticated user's profile."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={200: ProfileEnvelopeSerializer})
    def get(self, request: Request) -> Response:
        """Return the authenticated user's profile."""
        profile = services.get_or_create_profile(user=request.user)
        return success_response(ProfileOutputSerializer(profile).data)

    @extend_schema(
        request=ProfileUpdateInputSerializer,
        responses={200: ProfileEnvelopeSerializer},
    )
    def patch(self, request: Request) -> Response:
        """Update the authenticated user's profile."""
        serializer = ProfileUpdateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = services.update_profile(
            user=request.user,
            timezone=serializer.validated_data["timezone"],
        )
        return success_response(ProfileOutputSerializer(profile).data)


class PasswordChangeView(APIView):
    """Change the authenticated user's password."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        request=PasswordChangeInputSerializer,
        responses={200: StatusEnvelopeSerializer},
    )
    def post(self, request: Request) -> Response:
        """Change the authenticated user's local password."""
        serializer = PasswordChangeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.change_password(user=request.user, **serializer.validated_data)
        return success_response({"status": "password_changed"})


class PasswordResetRequestView(APIView):
    """Accept password reset requests."""

    authentication_classes: tuple = ()
    permission_classes = (AllowAny,)
    throttle_scope = "password_reset"

    @extend_schema(
        request=PasswordResetRequestInputSerializer,
        responses={202: StatusEnvelopeSerializer},
    )
    def post(self, request: Request) -> Response:
        """Accept a password reset request without revealing account state."""
        serializer = PasswordResetRequestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_password_reset(email=serializer.validated_data["email"])
        return success_response(
            {"status": "accepted"},
            status_code=status.HTTP_202_ACCEPTED,
        )


class PasswordResetConfirmView(APIView):
    """Confirm password reset requests."""

    authentication_classes: tuple = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        request=PasswordResetConfirmInputSerializer,
        responses={200: StatusEnvelopeSerializer},
    )
    def post(self, request: Request) -> Response:
        """Confirm a password reset and change the user's password."""
        serializer = PasswordResetConfirmInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.confirm_password_reset(**serializer.validated_data)
        return success_response({"status": "password_reset"})


class PersonalAccessTokenListCreateView(APIView):
    """List and create personal access tokens."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={200: PersonalAccessTokenListEnvelopeSerializer})
    def get(self, request: Request) -> Response:
        """Return personal access tokens owned by the authenticated user."""
        tokens = selectors.personal_access_tokens_for_user(user=request.user)
        return success_response(PersonalAccessTokenOutputSerializer(tokens, many=True).data)

    @extend_schema(
        request=PersonalAccessTokenCreateInputSerializer,
        responses={201: PersonalAccessTokenCreateEnvelopeSerializer},
    )
    def post(self, request: Request) -> Response:
        """Create a personal access token and return the raw token once."""
        serializer = PersonalAccessTokenCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token, raw_token = services.create_personal_access_token(
            user=request.user,
            name=serializer.validated_data["name"],
            scopes=serializer.validated_data["scopes"],
            expires_at=serializer.validated_data["expires_at"],
        )
        response_data = PersonalAccessTokenOutputSerializer(token).data
        response_data["token"] = raw_token
        return success_response(
            response_data,
            status_code=status.HTTP_201_CREATED,
        )


class PersonalAccessTokenDetailView(APIView):
    """Revoke personal access tokens."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={204: None})
    def delete(self, request: Request, token_id: int) -> Response:
        """Revoke a personal access token owned by the authenticated user."""
        services.revoke_personal_access_token(user=request.user, token_id=token_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserSearchView(APIView):
    """Search active users."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={200: UserSearchPaginatedEnvelopeSerializer})
    def get(self, request: Request) -> Response:
        """Return active users matching the search term."""
        users = selectors.search_active_users(request.query_params.get("q"))
        paginator = StandardPageNumberPagination()
        page = paginator.paginate_queryset(users, request, view=self)
        serializer = UserOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
