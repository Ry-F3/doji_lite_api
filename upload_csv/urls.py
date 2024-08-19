from django.urls import path
from .views import UploadFileView, CsvTradeView, LiveTradesListView

urlpatterns = [
    path('upload/', UploadFileView.as_view(), name='upload-file'),
    path('trades-csv/', CsvTradeView.as_view(), name='csv-trade'),
    path('live-trades/', LiveTradesListView.as_view(), name='live_trades_list'),
]
