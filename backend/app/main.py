
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router

from app.api.equipment import router as equipment_router

app = FastAPI(
    title="NexaSense API",
    description="AI-Powered Autonomous Inspection Robot Backend",
    version="1.0.0",
)

# Allow the React frontend to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type", "Authorization"],
)

# Register authentication routes
app.include_router(auth_router)
app.include_router(equipment_router)


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
