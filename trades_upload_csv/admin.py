from django.contrib import admin
from .models import TradeUploadBlofin, LiveTrades
from decimal import Decimal
from django.utils.translation import gettext_lazy as _
from django.db.models import Min, Max


class LiveTradesAdmin(admin.ModelAdmin):
    list_display = ('owner', 'asset', 'total_quantity', 'last_updated')
    list_filter = ('owner', 'last_updated')
    # Assuming `owner` is a ForeignKey to the User model
    search_fields = ('asset', 'owner__username')
    ordering = ('-last_updated',)
    readonly_fields = ('last_updated',)  # Optionally make fields read-only


admin.site.register(LiveTrades, LiveTradesAdmin)


class TradeUploadCsvAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'owner',
        'underlying_asset',
        'leverage',
        'order_time',
        'side',
        # 'formatted_avg_fill',
        # 'formatted_price',
        'formatted_filled',
        'original_filled',
        # 'formatted_pnl',
        # 'unrealized_net_pnl',
        # 'formatted_total_pnl_per_asset',
        # 'formatted_net_pnl',
        # 'formatted_pnl_percentage',
        # 'fee',
        # 'trade_status',
        'is_open',
        'is_matched',
        'is_partially_matched',
        'last_updated'
    )
    list_filter = (
        'owner',
        'underlying_asset',
        'side',
        'trade_status',
        'order_time',
        'is_open',
        'is_matched',
        'is_partially_matched'
    )
    search_fields = (
        'underlying_asset',
        'order_time',
        'side',
        'trade_status',
        'is_open',
        'is_matched'

    )
    ordering = ('-order_time', )  # Order by order_time descending by default

    def get_decimal_places(self, price):
        """Determine the number of decimal places needed for the given price."""
        if price is None:
            return 2  # Default decimal places if price is None

        abs_price = abs(price)
        if abs_price < 0.01:
            return 4
        elif abs_price < 1:
            return 3
        elif abs_price < 10:
            return 2
        else:
            return 2

    def formatted_avg_fill(self, obj):
        """Format avg_fill with conditional decimal places."""
        if obj.avg_fill is not None:
            avg_fill_value = Decimal(obj.avg_fill)
            decimal_places = self.get_decimal_places(avg_fill_value)
            return f"{avg_fill_value:.{decimal_places}f}"
        return 'N/A'

    def formatted_filled(self, obj):
        """Format filled with conditional decimal places."""
        if obj.filled is not None:
            filled_value = Decimal(obj.filled)
            decimal_places = self.get_decimal_places(filled_value)
            return f"{filled_value:.{decimal_places}f}"
        return 'N/A'

    def formatted_pnl(self, obj):
        """Format pnl based on conditions."""
        # Check if avg_fill equals price and set to '--'
        if obj.avg_fill == obj.price:
            return '--'

        # Check if trade is closed, price is 0.0, and pnl is 0.0
        if not obj.is_open and obj.price == Decimal('0.0') and obj.pnl == Decimal('0.0'):
            return '--'

        # Check if pnl is not None and format it
        if obj.pnl is not None:
            pnl_value = Decimal(obj.pnl)
            decimal_places = self.get_decimal_places(pnl_value)
            return f"{pnl_value:.{decimal_places}f}"

        return 'N/A'

    def formatted_pnl_percentage(self, obj):
        """Format pnl_percentage based on conditions."""
        # Check if avg_fill equals price and set to '--'
        if obj.avg_fill == obj.price:
            return '--'

        # Check if trade is closed, price is 0.0, and pnl_percentage is 0.0
        if not obj.is_open and obj.price == Decimal('0.0') and obj.pnl_percentage == Decimal('0.0'):
            return '--'

        # Check if pnl_percentage is not None and format it
        return f"{obj.pnl_percentage:.2f}%" if obj.pnl_percentage is not None else 'N/A'

    def formatted_price(self, obj):
        """Show price based on is_open status and automatic decimal places."""

        # Check if avg_fill equals price and set to '--'
        if obj.avg_fill == obj.price:
            return '--'

        # Check if trade is closed and price is 0.0
        if not obj.is_open and obj.price == Decimal('0.0'):
            return '--'

        # Check if price is not None and format it
        if obj.price is not None:
            decimal_places = self.get_decimal_places(obj.price)
            return f"{obj.price:.{decimal_places}f}"

        return 'N/A'

    def formatted_total_pnl_per_asset(self, obj):
        """Format previous_total_pnl_per_asset as PNL ASSET CLASS."""
        if obj.previous_total_pnl_per_asset is not None:
            pnl_value = Decimal(obj.previous_total_pnl_per_asset)
            decimal_places = self.get_decimal_places(pnl_value)
            return f"{pnl_value:.{decimal_places}f}"
        return 'N/A'

    def formatted_net_pnl(self, obj):
        """Format realized_net_pnl as TOTAL PNL."""
        if obj.realized_net_pnl is not None:
            pnl_value = Decimal(obj.realized_net_pnl)
            decimal_places = self.get_decimal_places(pnl_value)
            return f"{pnl_value:.{decimal_places}f}"
        return 'N/A'

    formatted_pnl.admin_order_field = 'pnl'
    formatted_pnl_percentage.admin_order_field = 'pnl_percentage'

    formatted_avg_fill.short_description = 'Avg Fill'  # Label for the column
    formatted_filled.short_description = 'Filled'
    formatted_pnl.short_description = 'PNL'
    formatted_pnl_percentage.short_description = 'PNL %'
    formatted_price.short_description = 'Price'
    formatted_total_pnl_per_asset.short_description = 'PNL ASSET CLASS'
    formatted_net_pnl.short_description = 'REALIZED PNL'


admin.site.register(TradeUploadBlofin, TradeUploadCsvAdmin)
