from django.contrib import admin
from .models import TradeUploadBlofin


class TradeUploadCsvAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'owner',
        'underlying_asset',
        'leverage',
        'order_time',
        'side',
        'formatted_avg_fill',  # Use the custom method for avg_fill
        'formatted_filled',    # Use the custom method for filled
        'formatted_pnl',       # Use the custom method for pnl
        'formatted_pnl_percentage',  # Use the custom method for pnl_percentage
        'fee',
        'trade_status',
        'is_open',
        'is_matched'
    )
    list_filter = (
        'owner',
        'underlying_asset',
        'side',
        'trade_status',
        'order_time',
        'is_open',
        'is_matched'
    )
    search_fields = (
        'underlying_asset',
        'order_time',
        'side',
        'trade_status',
        'is_open',
        'is_matched'
    )
    ordering = ('-order_time',)  # Order by order_time descending by default

    def formatted_avg_fill(self, obj):
        """Format avg_fill with conditional decimal places."""
        if obj.avg_fill is not None:
            # Format with 2 decimals if avg_fill >= 1, otherwise with 6 decimals
            if obj.avg_fill >= 1:
                return f"{obj.avg_fill:.2f}"
            else:
                return f"{obj.avg_fill:.8f}"
        return 'N/A'

    def formatted_filled(self, obj):
        """Format quantity with conditional decimal places."""
        if obj.filled is not None:
            if obj.filled >= 1:
                return f"{obj.filled:.2f}"
            else:
                return f"{obj.filled:.8f}"
        return 'N/A'

    def formatted_pnl(self, obj):
        """Format pnl based on conditions."""
        if obj.side == 'Buy':
            if obj.pnl == 0.00:
                return '--'
            else:
                return f"{obj.pnl:.2f}"
        return f"{obj.pnl:.2f}" if obj.pnl is not None else 'N/A'

    def formatted_pnl_percentage(self, obj):
        """Format pnl_percentage based on conditions."""
        if obj.side == 'Buy':
            if obj.pnl_percentage == 0.00:
                return '--'
            else:
                return f"{obj.pnl_percentage:.2f}%"
        return f"{obj.pnl_percentage:.2f}%" if obj.pnl_percentage is not None else 'N/A'

    formatted_avg_fill.short_description = 'Avg Fill'  # Label for the column
    formatted_filled.short_description = 'Filled'
    formatted_pnl.short_description = 'PNL'
    formatted_pnl_percentage.short_description = 'PNL %'


admin.site.register(TradeUploadBlofin, TradeUploadCsvAdmin)
