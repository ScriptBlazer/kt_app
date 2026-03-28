from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'common'
    label = 'common'

    def ready(self):
        from common.signals import register_audit_signals

        register_audit_signals()
