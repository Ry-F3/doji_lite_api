from django.apps import AppConfig


class HistoricalDatasetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'historical_datasets'

    def ready(self):
        import historical_datasets.signals  # Importing the signals module to ensure signals are connected
