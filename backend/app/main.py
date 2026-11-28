
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.alerts import router as alerts_router
from app.api.auth import router as auth_router
from app.api.equipment import router as equipment_router
from app.api.inspections import router as inspections_router
from app.api.history import router as history_router
from app.api.sensor_readings import router as sensor_readings_router
from app.services.sensor_scheduler import sensor_scheduler
from app.api.equipment_monitoring import router as equipment_monitoring_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start simulated sensor collection.
    sensor_scheduler.start()

    try:
        yield
    finally:
        # Stop collection when the backend shuts down.
        sensor_scheduler.stop()


app = FastAPI(
    title="NexaSense API",
    description="AI-Powered Autonomous Inspection Robot Backend",
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
   allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


app.include_router(auth_router)
app.include_router(equipment_router)
app.include_router(inspections_router)
app.include_router(sensor_readings_router)
app.include_router(equipment_monitoring_router)
app.include_router(alerts_router)
app.include_router(history_router)

@app.get("/")
def root():
    return {
        "message": "Welcome to NexaSense API",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "NexaSense Backend",
    }
