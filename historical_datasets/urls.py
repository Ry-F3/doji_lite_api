from django.urls import path
from .views import HistoricalPnlListView

urlpatterns = [
    path('historical-pnl/', HistoricalPnlListView.as_view(), name='historical-pnl-list'),
]
