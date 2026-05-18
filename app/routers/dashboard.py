"""
Dashboard router — attendance calendar, summary cards, special events.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import attendance_service

router = APIRouter(prefix="/dashboard")
templates = Jinja2Templates(directory="app/templates")


@router.get("/{emp_code}", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    emp_code: str,
    month: Optional[int] = Query(default=None),
    year: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Main dashboard page.
    Loads employee info, summary cards, calendar data, and special events.
    """
    today = date.today()
    sel_month = month or today.month
    sel_year = year or today.year

    # Fetch employee with relationships
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models import Employee

    stmt = (
        select(Employee)
        .options(
            selectinload(Employee.branch_rel),
            selectinload(Employee.shift_rel),
        )
        .where(Employee.emp_code == emp_code)
    )
    result = await db.execute(stmt)
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Build data
    summary = await attendance_service.build_dashboard_summary(db, employee, sel_year, sel_month)
    calendar_days = await attendance_service.build_calendar(
        db, emp_code, employee.branch_id, sel_year, sel_month
    )
    special_events = await attendance_service.get_todays_special_events(db)
    leave_types = await attendance_service.get_leave_types(db)

    # Convert calendar days to serialisable dicts for JS
    cal_data = []
    for day in calendar_days:
        cal_data.append({
            "date": day.date.isoformat(),
            "day_of_week": day.day_of_week,
            "is_sunday": day.is_sunday,
            "is_holiday": day.is_holiday,
            "holiday_name": day.holiday_name,
            "attendance_value": float(day.attendance_value) if day.attendance_value is not None else None,
            "in_time": day.in_time,
            "out_time": day.out_time,
            "worked_hours": day.worked_hours,
            "late_by": day.late_by,
            "early_by": day.early_by,
            "comment": day.comment,
            "on_leave": day.on_leave,
            "leave_type": day.leave_type,
        })

    # Month navigation helpers
    import calendar as cal_mod
    month_name = cal_mod.month_name[sel_month]
    prev_month = sel_month - 1 if sel_month > 1 else 12
    prev_year = sel_year if sel_month > 1 else sel_year - 1
    next_month = sel_month + 1 if sel_month < 12 else 1
    next_year = sel_year if sel_month < 12 else sel_year + 1

    # First weekday of the month (0=Mon, 6=Sun) for grid offset
    first_weekday = date(sel_year, sel_month, 1).weekday()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "employee": employee,
        "summary": summary,
        "calendar_days": cal_data,
        "special_events": special_events,
        "leave_types": leave_types,
        "sel_month": sel_month,
        "sel_year": sel_year,
        "month_name": month_name,
        "prev_month": prev_month,
        "prev_year": prev_year,
        "next_month": next_month,
        "next_year": next_year,
        "first_weekday": first_weekday,
        "today": today.isoformat(),
    })
