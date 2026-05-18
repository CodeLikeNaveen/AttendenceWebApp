"""
Attendance Service — all business logic for calendar, summary,
special events, and leave operations.
"""

import calendar
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple, Dict

from sqlalchemy import select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import models, schemas


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _fmt_time(t) -> Optional[str]:
    """Format a time object to HH:MM string."""
    if t is None:
        return None
    if isinstance(t, str):
        return t[:5]
    return t.strftime("%H:%M")


def _working_days_in_month(year: int, month: int) -> int:
    """Count non-Sunday days in a given month."""
    _, last_day = calendar.monthrange(year, month)
    return sum(
        1 for d in range(1, last_day + 1)
        if date(year, month, d).weekday() != 6  # 6 = Sunday
    )


# ─── Branch Queries ───────────────────────────────────────────────────────────

async def get_all_branches(db: AsyncSession) -> List[models.Branch]:
    """Fetch all branches for the home page dropdown."""
    result = await db.execute(select(models.Branch).order_by(models.Branch.branch_name))
    return result.scalars().all()


# ─── Employee Validation ──────────────────────────────────────────────────────

async def validate_employee(
    db: AsyncSession,
    emp_code: str,
    emp_name: str,
    branch_id: int,
) -> Optional[models.Employee]:
    """
    Validate that emp_code + emp_name + branch match a single Active employee.
    Returns the Employee ORM object or None.
    """
    stmt = (
        select(models.Employee)
        .options(
            selectinload(models.Employee.branch_rel),
            selectinload(models.Employee.shift_rel),
        )
        .where(
            and_(
                func.lower(models.Employee.emp_code) == emp_code.strip().lower(),
                func.lower(models.Employee.emp_name) == emp_name.strip().lower(),
                models.Employee.branch_id == branch_id,
                func.lower(models.Employee.status) == "active",
            )
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ─── Leave Types ──────────────────────────────────────────────────────────────

async def get_leave_types(db: AsyncSession) -> List[models.LeaveType]:
    result = await db.execute(select(models.LeaveType).order_by(models.LeaveType.leave_type_name))
    return result.scalars().all()


# ─── Holiday Lookup ───────────────────────────────────────────────────────────

async def get_holidays_for_month(
    db: AsyncSession,
    year: int,
    month: int,
    branch_id: Optional[int] = None,
) -> Dict[date, str]:
    """Return {holiday_date: holiday_name} for the given month."""
    first_day = date(year, month, 1)
    _, last = calendar.monthrange(year, month)
    last_day = date(year, month, last)

    stmt = select(models.Holiday).where(
        and_(
            models.Holiday.holiday_date >= first_day,
            models.Holiday.holiday_date <= last_day,
        )
    )
    if branch_id:
        stmt = stmt.where(
            (models.Holiday.branch_id == branch_id) | (models.Holiday.branch_id.is_(None))
        )
    result = await db.execute(stmt)
    holidays = result.scalars().all()
    return {h.holiday_date: h.holiday_name for h in holidays}


# ─── Leave Lookup ─────────────────────────────────────────────────────────────

async def get_leaves_for_month(
    db: AsyncSession,
    emp_code: str,
    year: int,
    month: int,
) -> Dict[date, str]:
    """
    Return {leave_date: leave_type_name} for approved/pending leaves
    that overlap with the given month.
    """
    first_day = date(year, month, 1)
    _, last = calendar.monthrange(year, month)
    last_day = date(year, month, last)

    stmt = (
        select(models.Leave)
        .options(selectinload(models.Leave.leave_type_rel))
        .where(
            and_(
                models.Leave.emp_code == emp_code,
                models.Leave.from_date <= last_day,
                models.Leave.to_date >= first_day,
                models.Leave.status.in_(["Pending", "Approved"]),
            )
        )
    )
    result = await db.execute(stmt)
    leave_records = result.scalars().all()

    leave_map: Dict[date, str] = {}
    for leave in leave_records:
        # Expand date range
        cur = max(leave.from_date, first_day)
        end = min(leave.to_date, last_day)
        while cur <= end:
            leave_map[cur] = leave.leave_type_rel.leave_type_name if leave.leave_type_rel else "Leave"
            cur += timedelta(days=1)
    return leave_map


# ─── Attendance Lookup ────────────────────────────────────────────────────────

async def get_attendance_for_month(
    db: AsyncSession,
    emp_code: str,
    year: int,
    month: int,
) -> Dict[date, models.Attendance]:
    """Return {date: Attendance} for a given employee/month."""
    first_day = date(year, month, 1)
    _, last = calendar.monthrange(year, month)
    last_day = date(year, month, last)

    stmt = select(models.Attendance).where(
        and_(
            models.Attendance.emp_code == emp_code,
            models.Attendance.date >= first_day,
            models.Attendance.date <= last_day,
        )
    )
    result = await db.execute(stmt)
    records = result.scalars().all()
    return {r.date: r for r in records}


# ─── Calendar Builder ─────────────────────────────────────────────────────────

async def build_calendar(
    db: AsyncSession,
    emp_code: str,
    branch_id: Optional[int],
    year: int,
    month: int,
) -> List[schemas.CalendarDay]:
    """
    Build a list of CalendarDay objects for every day in the month,
    merging attendance, holidays, and leave data.
    """
    holidays = await get_holidays_for_month(db, year, month, branch_id)
    leaves = await get_leaves_for_month(db, emp_code, year, month)
    attendance_map = await get_attendance_for_month(db, emp_code, year, month)

    _, last_day_num = calendar.monthrange(year, month)
    days: List[schemas.CalendarDay] = []

    for day_num in range(1, last_day_num + 1):
        d = date(year, month, day_num)
        att = attendance_map.get(d)

        days.append(schemas.CalendarDay(
            date=d,
            day_of_week=d.weekday(),  # 0=Mon, 6=Sun
            is_sunday=(d.weekday() == 6),
            is_holiday=(d in holidays),
            holiday_name=holidays.get(d),
            attendance_value=att.attendance_value if att else None,
            in_time=_fmt_time(att.in_time) if att else None,
            out_time=_fmt_time(att.out_time) if att else None,
            worked_hours=str(att.worked_hours) if att and att.worked_hours else None,
            late_by=att.late_by if att else None,
            early_by=att.early_by if att else None,
            comment=att.comment if att else None,
            on_leave=(d in leaves),
            leave_type=leaves.get(d),
        ))

    return days


# ─── Dashboard Summary ────────────────────────────────────────────────────────

async def build_dashboard_summary(
    db: AsyncSession,
    employee: models.Employee,
    year: int,
    month: int,
) -> schemas.DashboardSummary:
    """Compute summary card values for the dashboard."""
    emp_code = employee.emp_code
    first_day = date(year, month, 1)
    _, last = calendar.monthrange(year, month)
    last_day = date(year, month, last)

    # ── Total Late (any attendance with a non-empty late_by this month) ──
    late_stmt = select(func.count()).where(
        and_(
            models.Attendance.emp_code == emp_code,
            models.Attendance.date >= first_day,
            models.Attendance.date <= last_day,
            models.Attendance.late_by.isnot(None),
            models.Attendance.late_by != "",
            models.Attendance.late_by != "00:00",
        )
    )
    late_result = await db.execute(late_stmt)
    total_late = late_result.scalar() or 0

    # ── Leave taken this month ──
    leave_stmt = select(func.count()).where(
        and_(
            models.Leave.emp_code == emp_code,
            models.Leave.from_date <= last_day,
            models.Leave.to_date >= first_day,
            models.Leave.status.in_(["Pending", "Approved"]),
        )
    )
    leave_result = await db.execute(leave_stmt)
    leave_taken = leave_result.scalar() or 0

    # ── Total present (sum of attendance_value where value > 0) ──
    present_stmt = select(func.coalesce(func.sum(models.Attendance.attendance_value), 0)).where(
        and_(
            models.Attendance.emp_code == emp_code,
            models.Attendance.date >= first_day,
            models.Attendance.date <= last_day,
            models.Attendance.attendance_value > 0,
        )
    )
    present_result = await db.execute(present_stmt)
    total_present = Decimal(str(present_result.scalar() or 0))

    # ── Working days in month (non-Sundays) ──
    working_days = _working_days_in_month(year, month)

    # ── Absent = working days − present ──
    total_absent = max(0, int(working_days - float(total_present)))

    # ── Shift info ──
    shift_info: Optional[str] = None
    if employee.shift_rel:
        s = employee.shift_rel
        shift_info = (
            f"{s.shift_name} "
            f"({_fmt_time(s.start_time)} – {_fmt_time(s.end_time)})"
        )

    return schemas.DashboardSummary(
        total_late=total_late,
        leave_taken_month=leave_taken,
        shift_info=shift_info,
        total_present_month=total_present,
        total_absent_month=total_absent,
        working_days_month=working_days,
    )


# ─── Special Events ───────────────────────────────────────────────────────────

async def get_todays_special_events(
    db: AsyncSession,
) -> List[schemas.SpecialEvent]:
    """Return employees with birthday or joining anniversary today."""
    today = date.today()
    events: List[schemas.SpecialEvent] = []

    stmt = (
        select(models.Employee)
        .options(selectinload(models.Employee.branch_rel))
        .where(func.lower(models.Employee.status) == "active")
    )
    result = await db.execute(stmt)
    all_employees = result.scalars().all()

    for emp in all_employees:
        branch_name = emp.branch_rel.branch_name if emp.branch_rel else None

        # Birthday check
        if emp.date_of_birth:
            dob = emp.date_of_birth
            if dob.month == today.month and dob.day == today.day:
                age = today.year - dob.year
                events.append(schemas.SpecialEvent(
                    emp_code=emp.emp_code,
                    emp_name=emp.emp_name,
                    designation=emp.designation,
                    department=emp.department,
                    branch_name=branch_name,
                    event_type="birthday",
                    years=age,
                ))

        # Work anniversary check
        if emp.date_of_joining:
            doj = emp.date_of_joining
            if doj.month == today.month and doj.day == today.day and doj.year != today.year:
                years = today.year - doj.year
                events.append(schemas.SpecialEvent(
                    emp_code=emp.emp_code,
                    emp_name=emp.emp_name,
                    designation=emp.designation,
                    department=emp.department,
                    branch_name=branch_name,
                    event_type="anniversary",
                    years=years,
                ))

    return events


# ─── Leave Application ────────────────────────────────────────────────────────

async def apply_leave(
    db: AsyncSession,
    data: schemas.LeaveApplicationIn,
) -> models.Leave:
    """Insert a new leave application."""
    if data.from_date > data.to_date:
        raise ValueError("From date cannot be after To date.")

    leave = models.Leave(
        emp_code=data.emp_code,
        from_date=data.from_date,
        to_date=data.to_date,
        leave_type_id=data.leave_type_id,
        reason=data.reason,
        status="Pending",
        applied_on=datetime.utcnow(),
    )
    db.add(leave)
    await db.commit()
    await db.refresh(leave)
    return leave
