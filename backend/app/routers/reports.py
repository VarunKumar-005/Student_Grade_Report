"""reports.py — Attainment reporting and CSV export router.

Endpoints:
    GET  /reports/attainment                     — subject-level JSON report
    GET  /reports/attainment/export/csv          — marks detail CSV download
    GET  /reports/attainment/summary/csv         — attainment summary CSV download
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.deps import CurrentUser, DBSession
from app.models.user import UserRole
from app.schemas.report import SubjectAttainmentReport
from app.services.report_service import (
    export_attainment_summary_csv,
    export_marks_csv,
    get_subject_attainment_report,
)

router = APIRouter(prefix='/reports', tags=['Reports'])


def _resolve_scope(
    current_user,
    department_id: Optional[int],
) -> Optional[int]:
    """Ensure HOD only requests their own department."""
    if current_user.role == UserRole.HOD:
        if department_id is not None and department_id != current_user.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='HOD can only view reports for their own department',
            )
        return current_user.department_id
    return department_id


@router.get(
    '/attainment',
    response_model=SubjectAttainmentReport,
    summary='Subject-level CO attainment report (JSON)',
)
def get_attainment_report(
    db: DBSession,
    current_user: CurrentUser,
    subject_id: Optional[int] = Query(default=None, description='Restrict to a single subject'),
    department_id: Optional[int] = Query(default=None, description='Filter by department ID'),
    section_id: Optional[int] = Query(default=None, description='Filter by section ID'),
) -> SubjectAttainmentReport:
    """Return average CO direct attainment per subject with scoping."""
    effective_dept_id = _resolve_scope(current_user, department_id)
    return get_subject_attainment_report(
        db,
        subject_id=subject_id,
        department_id=effective_dept_id,
        section_id=section_id,
    )


@router.get(
    '/attainment/export/csv',
    summary='Download marks detail CSV',
)
def export_marks_detail_csv(
    db: DBSession,
    current_user: CurrentUser,
    subject_id: Optional[int] = Query(default=None, description='Restrict export to a single subject'),
    department_id: Optional[int] = Query(default=None, description='Filter by department ID'),
    section_id: Optional[int] = Query(default=None, description='Filter by section ID'),
) -> StreamingResponse:
    """Stream a CSV file containing per-student mark records with derived fields."""
    effective_dept_id = _resolve_scope(current_user, department_id)
    csv_content = export_marks_csv(
        db,
        subject_id=subject_id,
        department_id=effective_dept_id,
        section_id=section_id,
    )
    filename = f'marks_detail{"_subject_" + str(subject_id) if subject_id else ""}.csv'
    return StreamingResponse(
        iter([csv_content]),
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.get(
    '/attainment/summary/csv',
    summary='Download attainment summary CSV',
)
def export_attainment_summary(
    db: DBSession,
    current_user: CurrentUser,
    subject_id: Optional[int] = Query(default=None, description='Restrict to a single subject'),
    department_id: Optional[int] = Query(default=None, description='Filter by department ID'),
    section_id: Optional[int] = Query(default=None, description='Filter by section ID'),
) -> StreamingResponse:
    """Stream a CSV file with subject-level average attainment and threshold flags."""
    effective_dept_id = _resolve_scope(current_user, department_id)
    csv_content = export_attainment_summary_csv(
        db,
        subject_id=subject_id,
        department_id=effective_dept_id,
        section_id=section_id,
    )
    filename = f'attainment_summary{"_subject_" + str(subject_id) if subject_id else ""}.csv'
    return StreamingResponse(
        iter([csv_content]),
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )
