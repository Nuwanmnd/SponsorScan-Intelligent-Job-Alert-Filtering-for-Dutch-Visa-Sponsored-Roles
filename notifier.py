
from plyer import notification
import logging

def send_notification(title, message):
    """Sends a desktop notification."""
    try:
        notification.notify(
            title=title,
            message=message,
            app_name='Gmail Job Alert',
            timeout=10
        )
        logging.info(f"Notification sent: {title} - {message}")
    except Exception as e:
        logging.error(f"Failed to send notification: {e}")
