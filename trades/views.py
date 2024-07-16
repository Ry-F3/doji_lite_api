import requests
from decimal import Decimal
from django.shortcuts import render
from rest_framework import generics, permissions, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from trades.models import Trade
from django.conf import settings
from .calculations import calculate_percentage_change, calculate_return_pnl
from .serializers import (TradesSerializer)

class TradesListView(generics.ListAPIView):
    queryset = Trade.objects.all()
    serializer_class = TradesSerializer

    def update_current_prices(self):
        trades = Trade.objects.all()
        for trade in trades:
            symbol = trade.symbol

            # Fetch data from the external API
            api_url = f'https://financialmodelingprep.com/api/v3/quote/{symbol}'
            params = {
                'apikey': settings.FMP_API_KEY,
            }

            # Print the full URL with parameters to the terminal
            full_url = f"{api_url}?apikey={params['apikey']}"
            print(f"Fetching data from URL: {full_url}")

            # Make the API request
            response = requests.get(api_url, params=params)

            if response.status_code != 200:
                continue

            data = response.json()
            if not data:
                continue

            # Assuming the data contains necessary details, you can extract and use them
            symbol_data = data[0]
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
            f'https://financialmodelingprep.com/api/v3/profile/{symbol}?', # Normal Assets
            f'https://financialmodelingprep.com/api/v3/quote/{symbol}?' # Cryptocurrency
        ]

        for api_url in apis:
            params = {
                'apikey': settings.FMP_API_KEY,
            }

                   # Print the full URL with parameters to the terminal
            full_url = f"{api_url}apikey={params['apikey']}"
            print(f"Fetching data from URL: {full_url}")

            response = requests.get(api_url, params=params)
            print(response.content)
            if response.status_code == 200:
                data = response.json()
                if data:
                    return data[0]

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
            f'https://financialmodelingprep.com/api/v3/profile/{symbol}?',  # Normal Assets
            f'https://financialmodelingprep.com/api/v3/quote/{symbol}?'    # Cryptocurrency
        ]

        for api_url in apis:
            params = {
                'apikey': settings.FMP_API_KEY,
            }

        response = requests.get(api_url, params=params)

        if response.status_code != 200:
            raise serializers.ValidationError(f"Failed to fetch current price for symbol {symbol}")

        data = response.json()
        if not data:
            raise serializers.ValidationError(f"No data found for symbol {symbol}")

        return Decimal(data[0]['price'])

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

        # Perform dummy calculations for return_pnl
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

