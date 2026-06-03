import os
import sys

PROJECT_HOME = os.path.dirname(os.path.abspath(__file__))
VENV_SITE_PACKAGES = (
    '/home/tvt/virtualenv/tvt/3.13/lib/python3.13/site-packages'
)

if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)

if os.path.isdir(VENV_SITE_PACKAGES) and VENV_SITE_PACKAGES not in sys.path:
    sys.path.insert(0, VENV_SITE_PACKAGES)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tvt.settings')

from tvt.wsgi import application
