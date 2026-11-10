
from fastapi import FastAPI

app = FastAPI(
    title="NexaSense API",
    description="Backend API for the AI-Powered Autonomous Inspection Robot",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "Welcome to NexaSense API",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "NexaSense Backend"
    }
