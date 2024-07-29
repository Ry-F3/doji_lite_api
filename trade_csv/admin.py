from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path
from django.utils.html import format_html
from django.shortcuts import render
from .models import Trade
from .utils import import_trades_from_csv


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ('underlying_asset', 'side',
                    'order_time', 'price', 'status')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-csv/', self.admin_site.admin_view(self.upload_csv),
                 name='upload-csv'),
        ]
        return custom_urls + urls

    def upload_csv(self, request):
        if request.method == 'POST':
            csv_file = request.FILES['file']
            import_trades_from_csv(csv_file)  # Call your CSV import function
            self.message_user(
                request, "CSV uploaded and processed successfully.")
            return HttpResponseRedirect("../")

        form_html = """
            <form method="post" enctype="multipart/form-data">
                <input type="file" name="file" accept=".csv" required>
                <button type="submit">Upload CSV</button>
            </form>
        """
        return render(request, 'admin/upload_csv.html', {'form_html': format_html(form_html)})
