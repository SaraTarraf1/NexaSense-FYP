import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.alert_notification import AlertNotification
from app.models.equipment import Equipment
from app.models.user import User
from app.services.alert_configuration import IN_APP_NOTIFICATION_CHANNEL


logger = logging.getLogger(__name__)
NOTIFICATION_BATCH_SIZE = 50


class NotificationDeliveryError(Exception):
    pass


def _publish_in_app(
    notification: AlertNotification, equipment_owner_id: int, recipient_is_active: bool
) -> None:
    if notification.channel != IN_APP_NOTIFICATION_CHANNEL:
        raise NotificationDeliveryError("The configured notification channel is unavailable.")
    if notification.recipient_user_id != equipment_owner_id or not recipient_is_active:
        raise NotificationDeliveryError("The recipient is no longer eligible for this alert.")

    # Delivered rows form the recipient's in-app inbox.
    notification.status = "delivered"


def dispatch_pending_alert_notifications(db: Session) -> None:
    """Publish committed alerts to the in-app inbox in a separate transaction."""
    pending = db.execute(
        select(AlertNotification, Equipment.user_id, User.is_active)
        .select_from(AlertNotification)
        .join(Alert, Alert.id == AlertNotification.alert_id)
        .join(Equipment, Equipment.id == Alert.equipment_id)
        .join(User, User.id == AlertNotification.recipient_user_id)
        .where(AlertNotification.status == "pending")
        .order_by(AlertNotification.id)
        .limit(NOTIFICATION_BATCH_SIZE)
        .with_for_update(of=AlertNotification, skip_locked=True)
    ).all()

    for notification, equipment_owner_id, recipient_is_active in pending:
        notification.attempted_at = datetime.now(timezone.utc)
        try:
            _publish_in_app(notification, equipment_owner_id, recipient_is_active)
        except NotificationDeliveryError as error:
            notification.status = "failed"
            notification.error_message = str(error)
        except Exception:
            logger.exception("Alert notification %s failed", notification.id)
            notification.status = "failed"
            notification.error_message = "In-app notification delivery failed."
