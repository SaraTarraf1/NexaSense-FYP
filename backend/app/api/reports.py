from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, get_db
from app.models.inspection import Inspection
from app.models.inspection_report import InspectionReport
from app.models.user import User
from app.schemas.history import HistoryPage
from app.schemas.inspection import InspectionResponse
from app.schemas.report import ReportCreate, ReportDetail, ReportSummary
from app.services.history_service import count_rows
from app.services.report_pdf import render_report_pdf
from app.services.report_service import describe_report, equipment_for_report, owned_reports, save_report

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/eligible/{equipment_id}", response_model=HistoryPage[InspectionResponse])
def eligible_inspections(
    equipment_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    equipment_for_report(db, equipment_id, user.id)
    query = select(Inspection).where(
        Inspection.equipment_id == equipment_id, Inspection.user_id == user.id, Inspection.status == "completed",
    )
    return {
        "items": db.scalars(query.order_by(Inspection.started_at.desc(), Inspection.id.desc()).offset(offset).limit(limit)).all(),
        "total": count_rows(db, query), "offset": offset, "limit": limit,
    }


@router.get("", response_model=HistoryPage[ReportSummary])
def list_reports(
    equipment_id: int | None = Query(None, gt=0),
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = owned_reports(user.id)
    if equipment_id is not None:
        equipment_for_report(db, equipment_id, user.id)
        query = query.where(InspectionReport.equipment_id == equipment_id)
    reports = db.scalars(query.order_by(
        InspectionReport.generated_at.desc(), InspectionReport.id.desc(),
    ).offset(offset).limit(limit))
    return {"items": [describe_report(report) for report in reports],
            "total": count_rows(db, query), "offset": offset, "limit": limit}


@router.post("", response_model=ReportDetail)
def generate_report(
    data: ReportCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    report = save_report(db, data.equipment_id, data.inspection_id, user.id)
    result = {**describe_report(report), "snapshot": report.snapshot}
    db.commit()
    return result


def get_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    report = db.scalar(owned_reports(user.id).where(InspectionReport.id == report_id))
    if report is None:
        raise HTTPException(404, "Report not found.")
    return report


@router.get("/{report_id}", response_model=ReportDetail)
def view_report(report: InspectionReport = Depends(get_report)):
    return {**describe_report(report), "snapshot": report.snapshot}


@router.get("/{report_id}/pdf", response_class=Response, responses={200: {"content": {"application/pdf": {}}}})
def download_report(report: InspectionReport = Depends(get_report)):
    return Response(
        render_report_pdf(report), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="nexasense-report-{report.id}.pdf"',
                 "Cache-Control": "private, no-store"},
    )
