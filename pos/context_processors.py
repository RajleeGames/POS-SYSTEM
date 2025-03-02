from .models import Notification

def notifications_context(request):
    """
    Adds `unread_notifications` and `unread_count` to the context
    for any authenticated user.
    """
    if request.user.is_authenticated:
        unread_notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).order_by('-created_at')
        return {
            'unread_notifications': unread_notifications,
            'unread_count': unread_notifications.count(),
        }
    return {}
