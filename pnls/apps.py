from django.apps import AppConfig


class PnlsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pnls'

    def ready(self):
        import pnls.signals  # Importing the signals module to ensure signals are connected