from django.urls import path 
from .views import (TradesListView)

urlpatterns = [
    path('trades/', TradesListView.as_view(), name='trades'),
]