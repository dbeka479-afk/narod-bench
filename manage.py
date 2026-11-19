#!/usr/bin/env python
"""Запуск: python manage.py runserver"""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "narod.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
