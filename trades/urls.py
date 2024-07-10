from django.urls import path 
from .views import (TradesListView, TradePost)

urlpatterns = [
    path('trades/', TradesListView.as_view(), name='trades'),
    path('trades/post', TradePost.as_view(), name='trades-post'),
]