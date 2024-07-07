release: python manage.py makemigrations && python manage.py migrate
web: gunicorn doji_lite_api.wsgi