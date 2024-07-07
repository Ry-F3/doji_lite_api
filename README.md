## Django rest framework setup

<br>

Please use this template: [Code Institute Gitpod Full Template](https://github.com/Code-Institute-Org/ci-full-template)

<br>

#### Development workspace setup

| Step | Description                                                                  | Command                                          |
|------|------------------------------------------------------------------------------|--------------------------------------------------|
| 1    | Install Django version less than 4                                           | `pip3 install 'django<4'`                        |
| 2    | Create a Django project                                                      | `django-admin startproject project_name .`       |
| 3    | Install Cloudinary Storage                                                   | `pip install django-cloudinary-storage`          |
| 4    | Install Pillow                                                                | `pip install Pillow`                             |
| 5    | Set up Cloudinary API Key                                                    | Create an `env.py` file with Cloudinary API key  |
| 6    | Update Django Settings                                                       | Add cloudinary and cloudinary_storage to `INSTALLED_APPS` in settings.py               |
| 7    | Specify Allowed Hosts                                                        | Add allowed hosts to `settings.py`               |
| 8    | Create a Django App                                                          | `python3 manage.py startapp app_name` e.g profiles,  <br> [models.py](https://github.com/Ry-F3/doji_lite_api/blob/main/profiles/models.py), <br> [views.py](https://github.com/Ry-F3/doji_lite_api/blob/main/profiles/views.py), <br>  [serializers.py](https://github.com/Ry-F3/doji_lite_api/blob/main/profiles/serializers.py), <br>  [permissons.py](https://github.com/Ry-F3/doji_lite_api/blob/main/doji_lite_api/permissions.py), <br> [urls.py](https://github.com/Ry-F3/doji_lite_api/blob/main/profiles/urls.py)        |
| 9    | Make Migrations                                                              | `python3 manage.py makemigrations`               |
| 10   | Apply Migrations                                                             | `python3 manage.py migrate`                      |
| 11   | Install Django REST Framework                                                | `pip install djangorestframework`                |
| 12   | Freeze requirements into requirements.txt file                               | `pip freeze > requirements.txt`                  |
| 13   | Run the Django development server                                            | `python3 manage.py runserver`                    |

<br>

#### JWT tokens, user registration, and cookies setup

| Step | Description                                                                                                    | Command                                          |
|------|----------------------------------------------------------------------------------------------------------------|--------------------------------------------------|
| 1    | Install `dj-rest-auth` package for JWT token authentication                                                   | `pip3 install dj-rest-auth==2.1.9`              |
| 2    | Add `rest_framework.authtoken` and `dj_rest_auth` to `INSTALLED_APPS`                                         | Add the apps to `INSTALLED_APPS` in `settings.py`|
| 3    | Include `dj_rest_auth.urls` in the main URL patterns list                                                        | Add `path('dj-rest-auth/', include('dj_rest_auth.urls'))` to `urls.py`                                        |
| 4    | Migrate the database schema for `dj-rest-auth`                                                                  | `python3 manage.py migrate`                     |
| 5    | Install `dj-rest-auth` with social authentication support                                                       | `pip install dj-rest-auth[with_social]==5.1.0`       |
| 6    | Add necessary apps for user registration to `INSTALLED_APPS`                                                     | Add apps to `INSTALLED_APPS` in `settings.py` including:<br>`'django.contrib.sites',`<br>`'allauth',`<br>`'allauth.account',`<br>`'allauth.socialaccount',`<br>`'dj_rest_auth.registration'`|
| 7   | Add `allauth.account.middleware.AccountMiddleware` to `MIDDLEWARE`                                             | Add `'allauth.account.middleware.AccountMiddleware'` to `MIDDLEWARE` in `settings.py`|
| 8    | Set the `SITE_ID` to 1                                                                                         | Set `SITE_ID = 1` in `settings.py`              |
| 9    | Include `dj_rest_auth.registration.urls` in the main URL patterns list                                         | Add `path('dj-rest-auth/registration/', include('dj_rest_auth.registration.urls'))` to `urls.py`           |
| 10    | Install `djangorestframework-simplejwt` package for JWT token support                                           | `pip install djangorestframework-simplejwt`     |
| 11  | Configure DRF authentication settings based on environment (development or production)                         | Update `REST_FRAMEWORK` settings in `settings.py` as follows: [Click here](https://github.com/Ry-F3/doji_lite_api/blob/main/settings_tutorial/rest_framework.py)|
| 12   | Enable token authentication in DRF by setting `REST_USE_JWT` to `True`                                          | Set `REST_USE_JWT = True` in `settings.py`      |
| 13   | Ensure JWT tokens are sent only over HTTPS by setting `JWT_AUTH_SECURE` to `True`                               | Set `JWT_AUTH_SECURE = True` in `settings.py`   |
| 14   | Specify the name of the authentication cookie by setting `JWT_AUTH_COOKIE`                                      | Set `JWT_AUTH_COOKIE = 'my-app-auth'` in `settings.py`|
| 15   | Specify the name of the refresh token cookie by setting `JWT_AUTH_REFRESH_COOKIE`                                | Set `JWT_AUTH_REFRESH_COOKIE = 'my-refresh-token'` in `settings.py`: [Click here](https://github.com/Ry-F3/doji_lite_api/blob/main/settings_tutorial/jwt_token.py) |
| 16    | Freeze requirements into requirements.txt file                               | `pip freeze > requirements.txt`                  |

#### env.py file

![env.py](/media/screenshots/env.py.jpg)

* Ensure to have the correct settings applied within settings.py file in order for the env.py to function correctly:
  * [os_getenv.py](https://github.com/Ry-F3/doji_lite_api/blob/main/settings_tutorial/os_getenv.py) *Use for reference*
  * [imports.py](https://github.com/Ry-F3/doji_lite_api/blob/main/settings_tutorial/imports.py) *Use for reference*

#### Requesting user details 

| Step | Description                                                                                                    | Command                                          |
|------|----------------------------------------------------------------------------------------------------------------|--------------------------------------------------|
| 1    | Create a `serializer.py` file in the main project folder.                                                    | (Create the file manually in your main app)                       |
| 2    | Add the following code to `serializer.py`.                                                                    | [Click here](https://github.com/Ry-F3/doji_lite_api/blob/main/doji_lite_api/serializers.py)                             |
|      |                                                                                                                |                                                   |
| 3    | Add the settings to `settings.py`.                                                                            | [Click here](https://github.com/Ry-F3/doji_lite_api/blob/main/settings_tutorial/rest_auth_serializers.py)                             |
|      |                                                                                                                |                                                   |
| 4    | Run the database migrations.                                                                                  | `python3 manage.py migrate`                      |

<br>

#### Setup <code>root_route</code>

| Step | Description                                                                                                    | Command                                          |
|------|----------------------------------------------------------------------------------------------------------------|--------------------------------------------------|
| 1    | Create a `views.py` file in the main project folder.                                                          | (Create the file manually in your main app)                       |
| 2    | Add a basic view for Django Rest Framework (DRF).                                                             | [Click here](https://github.com/Ry-F3/doji_lite_api/blob/main/doji_lite_api/views.py)                    |
| 3    | Add the URL pattern for the root route and import views.                                                      | Add the following line to the top of the `urls.py` file:<br>`from .views import root_route`<br>Then, add the URL pattern:<br>`path('', root_route),`                      |
