from django.contrib import admin
from .models import TradeUploadBlofin


class TradeUploadCsvAdmin(admin.ModelAdmin):
    list_display = (
        'owner',
        'underlying_asset',

        'leverage',
        'order_time',
        'side',
        'formatted_avg_fill',  # Use the custom method for avg_fill
        # 'price',
        'formatted_filled',
        # 'total',
        'pnl',
        'pnl_percentage',
        'fee',


        'trade_status',
    )
    list_filter = (
        'owner',
        'underlying_asset',
        'side',
        'trade_status',
        'order_time',
    )
    search_fields = (
        'underlying_asset',
        'order_time',
        'side',
        'trade_status',
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

    formatted_avg_fill.short_description = 'Avg Fill'  # Label for the column
    formatted_filled.short_description = 'Filled'


admin.site.register(TradeUploadBlofin, TradeUploadCsvAdmin)
