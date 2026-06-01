"""Accounts API URL routes."""

from django.urls import path
from django.urls.resolvers import URLPattern

from apps.accounts.api.views import (
    LogoutView,
    MeView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PersonalAccessTokenDetailView,
    PersonalAccessTokenListCreateView,
    ProfileView,
    RegisterView,
    UserSearchView,
    WrappedTokenObtainPairView,
    WrappedTokenRefreshView,
    WrappedTokenVerifyView,
)

urlpatterns: list[URLPattern] = [
    path("register/", RegisterView.as_view(), name="user-register"),
    path("token/", WrappedTokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("token/refresh/", WrappedTokenRefreshView.as_view(), name="token-refresh"),
    path("token/verify/", WrappedTokenVerifyView.as_view(), name="token-verify"),
    path("logout/", LogoutView.as_view(), name="user-logout"),
    path("me/", MeView.as_view(), name="user-me"),
    path("profile/", ProfileView.as_view(), name="user-profile"),
    path(
        "personal-tokens/",
        PersonalAccessTokenListCreateView.as_view(),
        name="personal-token-list",
    ),
    path(
        "personal-tokens/<int:token_id>/",
        PersonalAccessTokenDetailView.as_view(),
        name="personal-token-detail",
    ),
    path("password/", PasswordChangeView.as_view(), name="user-password-change"),
    path(
        "password-reset/request/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("search/", UserSearchView.as_view(), name="user-search"),
]
