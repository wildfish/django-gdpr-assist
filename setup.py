import os
import re
import sys
from setuptools import setup, find_packages


VERSION = '1.1.0'


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def runtests(args):
    "Run tests"
    import django
    from django.conf import settings
    from django.core.management import execute_from_command_line

    if not settings.configured:
        testenv = re.sub(
            r'[^a-zA-Z0-9]', '_',
            os.environ.get('TOXENV', '_'.join(str(v) for v in django.VERSION)),
        )

        SETTINGS = dict(
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.admin',
                'django.contrib.sessions',
                'django.contrib.contenttypes',
                'django.contrib.messages',
                'gdpr_assist',
                'tests',
                'tests.gdpr_assist_tests_app',
            ],
            MIDDLEWARE=[
                'django.middleware.common.CommonMiddleware',
                'django.contrib.sessions.middleware.SessionMiddleware',
                'django.contrib.auth.middleware.AuthenticationMiddleware',
                'django.contrib.messages.middleware.MessageMiddleware',
            ],
            TEMPLATES=[{
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'APP_DIRS': True,
                'OPTIONS': {
                    'context_processors': [
                        'django.contrib.auth.context_processors.auth',
                        'django.contrib.messages.context_processors.messages',
                    ],
                },
            }],
            GDPR_CAN_ANONYMISE_DATABASE=True,
            ROOT_URLCONF='tests.gdpr_assist_tests_app.urls',
        )

        # Backwards compatibility for middleware
        if django.VERSION < (1, 10):
            SETTINGS['MIDDLEWARE_CLASSES'] = SETTINGS['MIDDLEWARE']

        # Build database settings
        MEMORY_DATABASE = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
        DATABASE = MEMORY_DATABASE.copy()
        GDPR_DATABASE = MEMORY_DATABASE.copy()

        DATABASE['TEST'] = MEMORY_DATABASE.copy()
        GDPR_DATABASE['TEST'] = MEMORY_DATABASE.copy()

        engine = os.environ.get('DATABASE_ENGINE')
        if engine:
            if engine == "pgsql":
                DATABASE['ENGINE'] = 'django.db.backends.postgresql_psycopg2'
                DATABASE['HOST'] = 'localhost'
            elif engine == "mysql":
                DATABASE['ENGINE'] = 'django.db.backends.mysql'

                # Make sure test DB is going to be UTF8
                DATABASE['TEST'] = {
                    'CHARSET': 'utf8',
                    'COLLATION': 'utf8_general_ci',
                }

            else:
                raise ValueError("Unknown database engine")

            DATABASE['NAME'] = os.environ.get('DATABASE_NAME', 'test_gdpr_assist_%s' % testenv)
            for key in ['USER', 'PASSWORD', 'HOST', 'PORT']:
                if 'DATABASE_' + key in os.environ:
                    DATABASE[key] = os.environ['DATABASE_' + key]
        SETTINGS['DATABASES'] = {
            'default': DATABASE,
            'gdpr_log': GDPR_DATABASE,
        }
        SETTINGS['DATABASE_ROUTERS'] = ['gdpr_assist.routers.EventLogRouter']

        # Configure
        settings.configure(**SETTINGS)

    execute_from_command_line(args[:1] + ['test'] + (args[2:] or ['tests']))


if len(sys.argv) > 1 and sys.argv[1] == 'test':
    runtests(sys.argv)
    sys.exit()

setup(
    name="django-gdpr-assist",
    version=VERSION,
    author="Wildfish",
    author_email="developers@wildfish.com",
    description=("GDPR tools for Django sites"),
    license="BSD",
    keywords="django gdpr",
    url="https://github.com/wildfish/django-gdpr-assist",
    long_description=read('README.rst'),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Framework :: Django',
        'Framework :: Django :: 1.8',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Framework :: Django :: 2.1',
    ],
    install_requires=[
        'django-yaa-settings',
    ],
    extras_require={
        'dev': [
            # Testing
            'tox', 'pillow', 'model-mommy',

            # Docs
            'sphinx', 'sphinx-autobuild', 'sphinx_rtd_theme',
        ],
    },
    zip_safe=True,
    packages=find_packages(exclude=('docs', 'tests*',)),
    include_package_data=True,
)
