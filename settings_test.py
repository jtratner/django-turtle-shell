from pathlib import Path
ROOT_DIR = Path(__file__).parent
DEBUG=True
DATABASES={
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}
SECRET_KEY="whatever"
INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'turtle_shell',
    'graphene_django',
)

