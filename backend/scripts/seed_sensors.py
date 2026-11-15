
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.sensor import Sensor
from app.services.sensor_configuration import SENSOR_DEFINITIONS


def seed_sensors():
    """
    Register the configured sensors in PostgreSQL.

    Existing sensors are updated rather than duplicated.
    """

    with SessionLocal() as db:
        for sensor_type, config in SENSOR_DEFINITIONS.items():

            sensor = db.scalar(
                select(Sensor).where(
                    Sensor.sensor_type == sensor_type
                )
            )

            if sensor is None:
                sensor = Sensor(
                    sensor_type=sensor_type,
                    **config,
                )
                db.add(sensor)
                print(f"Created sensor: {sensor_type}")

            else:
                for field, value in config.items():
                    setattr(sensor, field, value)

                print(f"Updated sensor: {sensor_type}")

        db.commit()

    print("Sensor configuration completed successfully.")


if __name__ == "__main__":
    seed_sensors()
