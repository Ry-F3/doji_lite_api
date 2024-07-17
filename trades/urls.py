from django.urls import path 
from .views import (TradesListView, TradePostView, TradeDetailView, HistoricalPnlListView, RealizedProfitAPIView)

urlpatterns = [
    path('trades/', TradesListView.as_view(), name='trades'),
    path('trades/post', TradePostView.as_view(), name='trades-post'),
    path('trades/post/<int:pk>/', TradeDetailView.as_view(), name='trade-detail'),
    path('historical-pnl/', HistoricalPnlListView.as_view(), name='historical-pnl-list'),
    path('realized-profit/', RealizedProfitAPIView.as_view(), name='realized-profit'),
]