#!/usr/bin/env python
"""Run Django management commands."""

import os
import sys


def main() -> None:
    """Run the selected Django management command."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
