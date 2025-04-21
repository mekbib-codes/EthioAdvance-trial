from .models import Notification, UserNotification

def create_notification(actor, verb, content_object=None, child=None, recipients=None, extra_data=None, notification_type=Notification.NotificationTypes.INFO):
    """
    Utility function to create a notification and associate it with users.

    Args:
        actor (User): The user who triggered the notification.
        verb (str): The action verb (e.g., 'session.created', 'payment.failed').
        content_object (Model, optional): The object related to the notification (e.g., a session, payment).
        child (Child, optional): The child related to the notification, if applicable.
        recipients (QuerySet or list): A list or queryset of users who should receive the notification.
        extra_data (dict, optional): Additional context data for the notification.
        notification_type (str): The type of notification (INFO, WARNING, ERROR).

    Returns:
        Notification: The created notification instance.
    """
    # Create the Notification instance
    notification = Notification.objects.create(
        actor=actor,
        verb=verb,
        content_object=content_object,
        child=child,
        type=notification_type,
        extra_data=extra_data or {}
    )

    # Create UserNotification instances for each recipient
    if recipients:
        user_notifications = [
            UserNotification(user=user, notification=notification)
            for user in recipients
        ]
        UserNotification.objects.bulk_create(user_notifications)

    return notification