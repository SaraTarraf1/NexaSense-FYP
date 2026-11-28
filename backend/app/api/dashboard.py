from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, get_db
from app.models.user import User
from app.schemas.dashboard import DashboardOverview
from app.services.dashboard_service import dashboard_overview

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardOverview)
def get_dashboard(response: Response, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    response.headers["Cache-Control"] = "private, no-store"
    return dashboard_overview(db, user.id)
