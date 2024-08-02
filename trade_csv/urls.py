from django.urls import path
from .views import UploadFileView, CsvTradeView

urlpatterns = [
    path('upload1/', UploadFileView.as_view(), name='upload-file'),
    path('trades-csv1/', CsvTradeView.as_view(), name='csv-trade'),
]
