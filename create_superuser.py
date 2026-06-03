import os
import sys
import django

# Asegurar que el proyecto está en el path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Configuración Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tvt.settings')

django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

username = (
    os.environ.get('DJANGO_SUPERUSER_USERNAME')
    or os.environ.get('BOOTSTRAP_SUPERUSER_USERNAME')
    or 'tvt'
)
email = (
    os.environ.get('DJANGO_SUPERUSER_EMAIL')
    or os.environ.get('BOOTSTRAP_SUPERUSER_EMAIL')
    or 'admin@tvtavata.com'
)
password = (
    os.environ.get('DJANGO_SUPERUSER_PASSWORD')
    or os.environ.get('BOOTSTRAP_SUPERUSER_PASSWORD')
)

if not password:
    print('Superuser no creado: falta DJANGO_SUPERUSER_PASSWORD.')
    raise SystemExit(0)

user, created = User.objects.get_or_create(
    username=username,
    defaults={'email': email},
)
user.email = email
user.is_staff = True
user.is_superuser = True
user.set_password(password)
user.save()

action = 'creado' if created else 'actualizado'
print(f'Superuser {username} {action}.')
