"""
Pydantic schemas for request validation and response serialization.
"""

from datetime import date, time, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


# ─── Branch ──────────────────────────────────────────────────────────────────

class BranchOut(BaseModel):
    id: int
    branch_name: str
    branch_code: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Employee ─────────────────────────────────────────────────────────────────

class EmployeeValidationIn(BaseModel):
    """Form data submitted on the home page."""
    emp_code: str = Field(..., min_length=1, max_length=50)
    emp_name: str = Field(..., min_length=1, max_length=200)
    branch_id: int


class EmployeeOut(BaseModel):
    id: int
    emp_code: str
    emp_name: str
    branch_id: Optional[int]
    shift_id: Optional[int]
    status: str
    date_of_birth: Optional[date]
    date_of_joining: Optional[date]
    designation: Optional[str]
    department: Optional[str]

    class Config:
        from_attributes = True


# ─── Shift ────────────────────────────────────────────────────────────────────

class ShiftOut(BaseModel):
    id: int
    shift_name: str
    start_time: Optional[time]
    end_time: Optional[time]
    total_hours: Optional[Decimal]

    class Config:
        from_attributes = True


# ─── Attendance ───────────────────────────────────────────────────────────────

class AttendanceOut(BaseModel):
    id: int
    emp_code: str
    date: date
    in_time: Optional[time]
    out_time: Optional[time]
    worked_hours: Optional[Decimal]
    late_by: Optional[str]
    early_by: Optional[str]
    attendance_value: Optional[Decimal]
    comment: Optional[str]

    class Config:
        from_attributes = True


# ─── Holiday ──────────────────────────────────────────────────────────────────

class HolidayOut(BaseModel):
    id: int
    holiday_date: date
    holiday_name: str

    class Config:
        from_attributes = True


# ─── Leave ────────────────────────────────────────────────────────────────────

class LeaveTypeOut(BaseModel):
    id: int
    leave_type_name: str
    max_days: Optional[int]

    class Config:
        from_attributes = True


class LeaveApplicationIn(BaseModel):
    """Form data for applying leave."""
    emp_code: str
    from_date: date
    to_date: date
    leave_type_id: int
    reason: Optional[str] = None


class LeaveOut(BaseModel):
    id: int
    emp_code: str
    from_date: date
    to_date: date
    leave_type_id: int
    reason: Optional[str]
    status: str
    applied_on: datetime

    class Config:
        from_attributes = True


# ─── Dashboard Summary ────────────────────────────────────────────────────────

class DashboardSummary(BaseModel):
    total_late: int
    leave_taken_month: int
    shift_info: Optional[str]
    total_present_month: Decimal
    total_absent_month: int
    working_days_month: int


# ─── Calendar Day ─────────────────────────────────────────────────────────────

class CalendarDay(BaseModel):
    date: date
    day_of_week: int          # 0=Mon … 6=Sun
    is_sunday: bool
    is_holiday: bool
    holiday_name: Optional[str] = None
    attendance_value: Optional[Decimal] = None
    in_time: Optional[str] = None
    out_time: Optional[str] = None
    worked_hours: Optional[str] = None
    late_by: Optional[str] = None
    early_by: Optional[str] = None
    comment: Optional[str] = None
    on_leave: bool = False
    leave_type: Optional[str] = None


# ─── Special Events ───────────────────────────────────────────────────────────

class SpecialEvent(BaseModel):
    emp_code: str
    emp_name: str
    designation: Optional[str]
    department: Optional[str]
    branch_name: Optional[str]
    event_type: str   # "birthday" or "anniversary"
    years: Optional[int] = None
