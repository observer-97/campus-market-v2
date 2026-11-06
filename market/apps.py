from django.apps import AppConfig

class MarketConfig(AppConfig):
    name = 'market'
    verbose_name = '校园交易'
    def ready(self):
        from . import signals
