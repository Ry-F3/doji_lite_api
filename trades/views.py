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

        
class TradePostView(generics.CreateAPIView):
    queryset = Trade.objects.all()
    serializer_class= TradesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        entry_price = serializer.validated_data['entry_price']
        current_price = serializer.validated_data['current_price']
        margin = serializer.validated_data['margin']
        leverage = serializer.validated_data['leverage']
        
        # Dummy calculations return_pnl
        return_pnl = (current_price - entry_price) * margin * leverage

        # Save the trade with the calculated return_pnl
        serializer.save(user=self.request.user, return_pnl=return_pnl)

class TradeDetailView(generics.RetrieveUpdateDestroyAPIView):
    querset = Trade.objects.all()
    serializer_class = TradesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        trade_id = self.kwargs.get('pk')
        return Trade.objects.filter(pk=trade_id)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Perform dummy calculations for return_pnl
        entry_price = serializer.validated_data['entry_price']
        current_price = serializer.validated_data['current_price']
        margin = serializer.validated_data['margin']
        leverage = serializer.validated_data['leverage']
        
        return_pnl = (current_price - entry_price) * margin * leverage

        # Update the trade with the calculated return_pnl
        serializer.save(return_pnl=return_pnl)

        return Response(serializer.data)

