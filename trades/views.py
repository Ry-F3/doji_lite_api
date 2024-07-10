from django.shortcuts import render
from rest_framework import generics, serializers
from rest_framework.views import APIView
from trades.models import Trade
from .serializers import (TradesSerializer)

class TradesListView(generics.ListAPIView):
    queryset = Trade.objects.all()
    serializer_class = TradesSerializer
