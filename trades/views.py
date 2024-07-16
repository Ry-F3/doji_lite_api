import requests
from decimal import Decimal
from django.shortcuts import render
from rest_framework import generics, permissions, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from trades.models import Trade
from django.conf import settings
from .api_handlers import fetch_quote, fetch_profile
from .calculations import calculate_percentage_change, calculate_return_pnl
from .serializers import (TradesSerializer)

class TradesListView(generics.ListAPIView):
    queryset = Trade.objects.all()
    serializer_class = TradesSerializer

    def update_current_prices(self):
        trades = Trade.objects.all()
        for trade in trades:
            symbol = trade.symbol

            apis = [
                fetch_profile,  # Normal Assets
                fetch_quote     # Cryptocurrency
            ]

            symbol_data = None
            for api_function in apis:
                symbol_data = api_function(symbol)
                if symbol_data:
                    break

            if not symbol_data:
                continue

            current_price = symbol_data.get('price')

            if current_price is None:
                continue

            # Convert current_price to decimal.Decimal
            current_price = Decimal(current_price)

            # Update the trade's current price
            trade.current_price = current_price

             # Calculate percentage change and return PnL
            trade.percentage_change = calculate_percentage_change(
                current_price, trade.entry_price, trade.leverage, trade.long_short
            )

            trade.return_pnl = calculate_return_pnl(trade.percentage_change, trade.margin)

            trade.percentage = trade.percentage_change

            trade.save()

    def list(self, request, *args, **kwargs):
        # Update current prices before returning the list
        self.update_current_prices()

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

    def fetch_data_from_api(self, symbol):

        apis = [
            fetch_profile, # Normal Assets
            fetch_quote    # Cryptocurrency
        ]

        for api_function in apis:
            symbol_data = api_function(symbol)
            if symbol_data:
                return symbol_data

        raise serializers.ValidationError("No data found for the given symbol in any API")


    def perform_create(self, serializer):
        symbol = serializer.validated_data['symbol']
        entry_price = serializer.validated_data['entry_price']
        margin = serializer.validated_data['margin']
        leverage = serializer.validated_data['leverage']
        long_short = serializer.validated_data['long_short']

        # Fetch data from the external API
        symbol_data = self.fetch_data_from_api(symbol)
        current_price = symbol_data.get('price')

        if current_price is None:
            raise serializers.ValidationError("Current price not available for the given symbol")

        # Convert current_price to decimal.Decimal
        current_price = Decimal(current_price)

        # Calculate percentage change and return PnL
        percentage_change = calculate_percentage_change(
            current_price, entry_price, leverage, long_short
        )
        return_pnl = calculate_return_pnl(percentage_change, margin)

        percentage = percentage_change

        # Save the trade with the calculated return_pnl and current price
        serializer.save(user=self.request.user, return_pnl=return_pnl, current_price=current_price, percentage=percentage)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class TradeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Trade.objects.all()
    serializer_class = TradesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        trade_id = self.kwargs.get('pk')
        return generics.get_object_or_404(Trade, pk=trade_id)

    def fetch_current_price(self, symbol):
        
        apis = [
            fetch_profile, # Normal Assets
            fetch_quote    # Cryptocurrency
        ]

        for api_function in apis:
            symbol_data = api_function(symbol)
            if symbol_data:
                return Decimal(symbol_data['price'])

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        
        # Debug prints to inspect request data
        print(f"Request data: {request.data}")

        serializer.is_valid(raise_exception=True)

        # Ensure current_price is included in the request data
        current_price = serializer.validated_data.get('current_price')
        if current_price is None:
            raise serializers.ValidationError("Current price is required.")

        # Convert current_price to decimal.Decimal
        current_price = Decimal(current_price)

        # Perform calculations for return_pnl
        entry_price = serializer.validated_data['entry_price']
        current_price = serializer.validated_data['current_price']
        margin = serializer.validated_data['margin']
        leverage = serializer.validated_data['leverage']
        long_short = serializer.validated_data['long_short']

        # Calculate percentage change and return PnL
        percentage_change = calculate_percentage_change(
            current_price, entry_price, leverage, long_short
        )
        return_pnl = calculate_return_pnl(percentage_change, margin)

        percentage = percentage_change

        # Save the trade with the calculated return_pnl and current price
        serializer.save(user=self.request.user, return_pnl=return_pnl, current_price=current_price, percentage=percentage)

        return Response(serializer.data)

