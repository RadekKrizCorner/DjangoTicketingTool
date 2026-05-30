"""Local development Django settings."""

from decouple import Csv, config

from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS",
    default="localhost,127.0.0.1,testserver,api",
    cast=Csv(),
)
