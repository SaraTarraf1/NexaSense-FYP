
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router


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
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Register authentication routes
app.include_router(auth_router)


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
