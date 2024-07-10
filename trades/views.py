from django.shortcuts import render
from rest_framework import generics, permissions, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from trades.models import Trade
from .serializers import (TradesSerializer)

class TradesListView(generics.ListAPIView):
    queryset = Trade.objects.all()
    serializer_class = TradesSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response(
                {"error": "No Trades Exist"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

        
class TradePost(generics.CreateAPIView):
    queryset = Trade.objects.all()
    serializer_class= TradesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)