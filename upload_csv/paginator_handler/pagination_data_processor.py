class CustomPagination(PageNumberPagination):
    page_size = 10  # Default page size
    # Allow clients to override, e.g., ?page_size=20
    page_size_query_param = 'page_size'
    max_page_size = 100  # Maximum page size allowed

    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate the queryset, updating the data only when a specific page is requested.
        """
        # Get the updated queryset for the specific page

        return super().paginate_queryset(queryset, request, view)
