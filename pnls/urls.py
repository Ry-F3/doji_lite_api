from django.urls import path
from .views import RealizedProfitAPIView

urlpatterns = [
    path('realized-profit/', RealizedProfitAPIView.as_view(), name='realized-profit'),
]
