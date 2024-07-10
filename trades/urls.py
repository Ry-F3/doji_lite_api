from django.urls import path 
from .views import (TradesListView, TradePostView, TradeDetailView)

urlpatterns = [
    path('trades/', TradesListView.as_view(), name='trades'),
    path('trades/post', TradePostView.as_view(), name='trades-post'),
    path('trades/post/<int:pk>/', TradeDetailView.as_view(), name='trade-detail'),
]