from django.urls import path
from .views import UploadFileView, CsvTradeView

urlpatterns = [
    path('upload/', UploadFileView.as_view(), name='upload-file'),
    path('trades-csv/', CsvTradeView.as_view(), name='csv-trade'),
]
