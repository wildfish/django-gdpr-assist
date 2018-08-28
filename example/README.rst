======================================
Example project for django-gdpr-assist
======================================

This example project is configured for Django 1.11.

To set it up and run it in a self-contained virtualenv::

    virtualenv gdpr-example
    cd gdpr-example
    source bin/activate
    pip install -e git+https://github.com/wildfish/django-gdpr-assist.git#egg=django-gdpr-assist
    cd src/django-gdpr-assist/example
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py migrate --database=gdpr_log
    python manage.py createsuperuser
    python manage.py runserver 0:8000

You can then visit the example site at http://localhost:8000/ and the
admin site at http://localhost:8000/admin/
