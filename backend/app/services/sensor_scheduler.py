
import logging
import threading

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.inspection import Inspection
from app.services.alert_notification_service import dispatch_pending_alert_notifications
from app.services.sensor_collection_service import (
    collect_inspection_readings,
)


logger = logging.getLogger(__name__)


class SensorScheduler:
    """
    Background scheduler for sensor collection and in-app notification delivery.

    Runs every second and checks whether readings are due.
    Each sensor's configured interval determines when
    a new measurement is generated.
    """

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="nexasense-sensor-scheduler",
        )

        self._thread.start()
        logger.info("Sensor scheduler started.")

    def stop(self):
        self._stop_event.set()

        if self._thread is not None:
            self._thread.join(timeout=10)

        logger.info("Sensor scheduler stopped.")

    def _run(self):
        while not self._stop_event.is_set():
            try:
                self._collect_active_inspections()
            except Exception:
                logger.exception("Sensor scheduler cycle failed.")

            try:
                with SessionLocal.begin() as db:
                    dispatch_pending_alert_notifications(db)
            except Exception:
                logger.exception("Alert notification dispatch cycle failed.")

            self._stop_event.wait(1)

    def _collect_active_inspections(self):
        # Fetch active inspection IDs.
        with SessionLocal() as db:
            inspection_ids = db.scalars(
                select(Inspection.id).where(
                    Inspection.status == "active"
                )
            ).all()

        for inspection_id in inspection_ids:
            if self._stop_event.is_set():
                break

            try:
                with SessionLocal() as db:
                    readings = collect_inspection_readings(
                        db,
                        inspection_id,
                    )

                    db.commit()

                    if readings:
                        logger.info(
                            "Collected %s readings for inspection %s",
                            len(readings),
                            inspection_id,
                        )

            except Exception:
                logger.exception(
                    "Collection failed for inspection %s",
                    inspection_id,
                )


sensor_scheduler = SensorScheduler()
