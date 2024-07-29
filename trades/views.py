import requests
from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, permissions, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from trades.models import Trade
from historical_datasets.models import HistoricalPnl
from django.conf import settings
from .api_handlers import fetch_quote, fetch_profile
from .calculations import calculate_percentage_change, calculate_return_pnl
from rest_framework.permissions import IsAuthenticated
from .serializers import (TradesSerializer)


@csrf_exempt
def search_asset(request):
    if request.method == 'GET':
        symbol = request.GET.get('symbol')
        if not symbol:
            return JsonResponse({'error': 'Symbol is required'}, status=400)

        # Fetch data from both APIs
        quote_data = fetch_quote(symbol)
        profile_data = fetch_profile(symbol)

        # Combine data
        if quote_data and profile_data:
            combined_data = {
                'symbol': quote_data.get('symbol'),
                'name': profile_data.get('name'),
                'price': quote_data.get('price'),
                'changesPercentage': quote_data.get('changesPercentage'),
                'change': quote_data.get('change'),
                'dayLow': quote_data.get('dayLow'),
                'dayHigh': quote_data.get('dayHigh'),
                'yearHigh': quote_data.get('yearHigh'),
                'yearLow': quote_data.get('yearLow'),
                'marketCap': quote_data.get('marketCap'),
                'priceAvg50': quote_data.get('priceAvg50'),
                'priceAvg200': quote_data.get('priceAvg200'),
                'exchange': quote_data.get('exchange'),
                'volume': quote_data.get('volume'),
                'avgVolume': quote_data.get('avgVolume'),
                'open': quote_data.get('open'),
                'previousClose': quote_data.get('previousClose'),
                'eps': quote_data.get('eps'),
                'pe': quote_data.get('pe'),
                'earningsAnnouncement': quote_data.get('earningsAnnouncement'),
                'sharesOutstanding': quote_data.get('sharesOutstanding'),
                'timestamp': quote_data.get('timestamp'),
            }
            return JsonResponse(combined_data)
        else:
            return JsonResponse({'error': 'No data found for the given symbol'}, status=404)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


class TradesListView(generics.ListAPIView):
    queryset = Trade.objects.all()
    serializer_class = TradesSerializer

    def update_current_prices(self):
        trades = Trade.objects.filter(
            is_trade_closed=False)  # Filter out closed trades
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

            trade.return_pnl = calculate_return_pnl(
                trade.percentage_change, trade.margin)

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
    serializer_class = TradesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def fetch_data_from_api(self, symbol):

        apis = [
            fetch_profile,  # Normal Assets
            fetch_quote    # Cryptocurrency
        ]

        for api_function in apis:
            symbol_data = api_function(symbol)
            if symbol_data:
                return symbol_data

        raise serializers.ValidationError(
            "No data found for the given symbol in any API")

    def perform_create(self, serializer):
        symbol = serializer.validated_data['symbol']
        entry_price = serializer.validated_data['entry_price']
        margin = serializer.validated_data['margin']
        leverage = serializer.validated_data['leverage']
        long_short = serializer.validated_data['long_short']
        is_trade_closed = serializer.validated_data.get(
            'is_trade_closed', False)

        # Fetch data from the external API
        symbol_data = self.fetch_data_from_api(symbol)
        current_price = symbol_data.get('price')

        if current_price is None:
            raise serializers.ValidationError(
                "Current price not available for the given symbol")

        # Convert current_price to decimal.Decimal
        current_price = Decimal(current_price)

        # Calculate percentage change and return PnL
        percentage_change = calculate_percentage_change(
            current_price, entry_price, leverage, long_short
        )
        return_pnl = calculate_return_pnl(percentage_change, margin)

        percentage = percentage_change

        # Save the trade with the calculated return_pnl and current price
        trade = serializer.save(user=self.request.user, return_pnl=return_pnl,
                                current_price=current_price, percentage=percentage)

        if is_trade_closed:
            HistoricalPnl.objects.create(
                user=self.request.user,
                date=trade.created_at,
                symbol=symbol,
                pnl=return_pnl
            )

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
            fetch_profile,  # Normal Assets
            fetch_quote    # Cryptocurrency
        ]

        for api_function in apis:
            symbol_data = api_function(symbol)
            if symbol_data:
                return Decimal(symbol_data['price'])

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=True)

        # Check if trade is closed before updating
        if instance.is_trade_closed:
            raise serializers.ValidationError("Cannot update a closed trade.")

        serializer.is_valid(raise_exception=True)

        # Ensure current_price is included in the request data or fallback to instance value
        current_price = serializer.validated_data.get(
            'current_price', instance.current_price)

        if current_price is None:
            raise serializers.ValidationError("Current price is required.")

        # Convert current_price to decimal.Decimal
        current_price = Decimal(current_price)

        # Perform calculations for return_pnl
        entry_price = serializer.validated_data['entry_price']
        # current_price = serializer.validated_data['current_price']
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
        serializer.save(user=self.request.user, return_pnl=return_pnl,
                        current_price=current_price, percentage=percentage)

        return Response(serializer.data)
