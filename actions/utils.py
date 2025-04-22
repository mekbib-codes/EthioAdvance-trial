from .models import Notification, UserNotification, ActivityLog
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

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

def create_activity_log(user, action, link, kwargs:dict|None=None, related_object=None):
    """
    Utility function to create an activity log entry.

    Args:
        user (User): The user who performed the action.
        action (str): A description of the action performed.
        related_object (Model, optional): The object related to the action (e.g., a child, session, or payment).

    Returns:
        ActivityLog: The created activity log instance.
    """
    try:
        # Determine the content type and object ID if a related object is provided
        content_type = ContentType.objects.get_for_model(related_object) if related_object else None
        object_id = related_object.id if related_object else None

        # Create the activity log entry
        activity_log = ActivityLog.objects.create(
            user=user,
            action=action,
            content_type=content_type,
            object_id=object_id,
            link=reverse(link, kwargs=kwargs)
        )
        return activity_log
    except Exception as e:
        # Log the error (optional)
        import logging
        logger = logging.getLogger('app')
        logger.error(f"Failed to create activity log: {str(e)}", exc_info=True)
        return None