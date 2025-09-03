#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def is_development_environment():
    """Determine if we're in a development environment based on multiple
    indicators. This avoids importing Django settings and potential
    circular dependencies.
    """
    # Check for explicit environment variable
    django_debug = os.environ.get("DJANGO_DEBUG", "").lower()
    if django_debug in ("true", "1", "yes", "on"):
        return True
    if django_debug in ("false", "0", "no", "off"):
        return False

    # Check for development indicators
    development_indicators = [
        os.environ.get("DJANGO_SETTINGS_MODULE") == "nitapi.settings.local",
        os.environ.get("ENVIRONMENT", "").lower() in (
            "dev", "development", "local"
        ),
        os.path.exists(".env"),  # Common in local development
        os.path.exists("docker-compose.yml"),  # Local development setup
        "--runserver" in sys.argv,  # Django development server
        any("runserver" in arg for arg in sys.argv),
    ]

    return any(development_indicators)


def main():
    """Run administrative tasks."""
    if is_development_environment():
        os.environ.setdefault(
            "DJANGO_SETTINGS_MODULE", "nitapi.settings.local"
        )
    else:
        os.environ.setdefault(
            "DJANGO_SETTINGS_MODULE", "nitapi.settings.production"
        )
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
