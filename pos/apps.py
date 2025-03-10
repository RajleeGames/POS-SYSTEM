# pos/apps.py
from django.apps import AppConfig

class PosConfig(AppConfig):
    name = 'pos'

    def ready(self):
        import pos.signals  # type: ignore # Keep this if you DO need to load signals on startup
