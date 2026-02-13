from django.apps import AppConfig

class ViewerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'viewer'

    def ready(self):
        from django.contrib.auth.models import User
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin",
                password="admin12345"
            )
