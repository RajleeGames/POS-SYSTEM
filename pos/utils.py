# pos/utils.py
from django.contrib.auth.models import User # type: ignore
from .models import Notification

def notify_user(user, message):
    """
    Create a new Notification for the given user.
    """
    if user and user.is_authenticated:
        Notification.objects.create(user=user, message=message)
