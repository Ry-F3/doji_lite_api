REST_USE_JWT = True  # enable token auth
JWT_AUTH_SECURE = True  # sent over https only
JWT_AUTH_COOKIE = 'my-app-auth'  # declare cookie name access
JWT_AUTH_REFRESH_COOKIE = 'my-refresh-token'  # declare cookie name refresh
JWT_AUTH_SAMESITE = 'None'