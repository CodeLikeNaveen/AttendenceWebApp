"""
Leave router — handles leave application form submission.
"""

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.database import get_db
from app.schemas import LeaveApplicationIn
from app.services import attendance_service

router = APIRouter(prefix="/leave")
templates = Jinja2Templates(directory="app/templates")


@router.post("/apply", response_class=HTMLResponse)
async def apply_leave(
    request: Request,
    emp_code: str = Form(...),
    from_date: date = Form(...),
    to_date: date = Form(...),
    leave_type_id: int = Form(...),
    reason: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    """
    Process leave application form submission.
    On success → redirect back to dashboard with success flag.
    On error   → redirect back with error message.
    """
    try:
        data = LeaveApplicationIn(
            emp_code=emp_code,
            from_date=from_date,
            to_date=to_date,
            leave_type_id=leave_type_id,
            reason=reason or None,
        )
        await attendance_service.apply_leave(db, data)
        return RedirectResponse(
            url=f"/dashboard/{emp_code}?leave_success=1",
            status_code=303,
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"/dashboard/{emp_code}?leave_error={str(e)}",
            status_code=303,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not apply leave: {str(e)}")
