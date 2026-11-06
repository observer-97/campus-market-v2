import os
import sys
from pathlib import Path

if not (3, 11) <= sys.version_info[:2] <= (3, 13):
    raise SystemExit('Please use Python 3.12, or run this project with run.ps1 (Python 3.11-3.13 supported).')
sys.path.insert(0, str(Path(__file__).resolve().parent / '.packages312'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
from django.core.management import execute_from_command_line
execute_from_command_line(sys.argv)
