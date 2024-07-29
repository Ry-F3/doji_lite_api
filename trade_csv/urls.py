from django.urls import path
from .views import upload_csv, get_trades

urlpatterns = [
    path('upload_csv/', upload_csv, name='upload_csv'),
    path('get_trades/', get_trades, name='get_trades'),
]
