release: python manage.py migrate --noinput
web: gunicorn camway.wsgi:application --workers 3 --timeout 60
