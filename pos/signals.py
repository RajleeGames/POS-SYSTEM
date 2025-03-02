from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from .models import LoginLog
from .utils import notify_user

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip = request.META.get('REMOTE_ADDR', '')
    LoginLog.objects.create(user=user, ip_address=ip)
    notify_user(user, f"{user.username} has logged in!")


