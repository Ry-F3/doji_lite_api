from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import HistoricalPnl
from .serializers import HistoricalPnlSerializer

class HistoricalPnlListView(generics.ListAPIView):
    queryset = HistoricalPnl.objects.all().order_by('date') 
    serializer_class = HistoricalPnlSerializer
    permission_classes = [IsAuthenticated]