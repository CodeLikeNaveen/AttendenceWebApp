"""
SQLAlchemy ORM Models for the Attendance Application.
Maps to existing database tables used by the desktop app.
"""

from datetime import date, time, datetime
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Date, Time, DateTime,
    Numeric, Boolean, ForeignKey, Text, Enum
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class EmployeeStatus(str, enum.Enum):
    active = "Active"
    inactive = "Inactive"
    terminated = "Terminated"


class Branch(Base):
    """Branch / office location table."""
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True)
    branch_name = Column(String(100), nullable=False, unique=True)
    branch_code = Column(String(20), nullable=True)

    # Relationships
    employees = relationship("Employee", back_populates="branch_rel")


class Shift(Base):
    """Work shift definitions (start/end times)."""
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    shift_name = Column(String(100), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    total_hours = Column(Numeric(5, 2), nullable=True)

    # Relationships
    employees = relationship("Employee", back_populates="shift_rel")


class Employee(Base):
    """Employee master table."""
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    emp_code = Column(String(50), nullable=False, unique=True, index=True)
    emp_name = Column(String(200), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=True)
    status = Column(String(20), nullable=False, default="Active")
    date_of_birth = Column(Date, nullable=True)
    date_of_joining = Column(Date, nullable=True)
    designation = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)

    # Relationships
    branch_rel = relationship("Branch", back_populates="employees")
    shift_rel = relationship("Shift", back_populates="employees")
    attendance_records = relationship("Attendance", back_populates="employee")
    leaves = relationship("Leave", back_populates="employee")


class Attendance(Base):
    """
    Daily attendance records.
    attendance_value: 1=Full Day, 0.75=3/4 Day, 0.5=Half Day,
                      0.25=Quarter, 0=Absent, -0.25=Penalty
    """
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    emp_code = Column(String(50), ForeignKey("employees.emp_code"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    in_time = Column(Time, nullable=True)
    out_time = Column(Time, nullable=True)
    worked_hours = Column(Numeric(5, 2), nullable=True)
    late_by = Column(String(20), nullable=True)    # e.g. "00:30" = 30 min late
    early_by = Column(String(20), nullable=True)   # e.g. "00:15" = 15 min early
    attendance_value = Column(Numeric(5, 2), nullable=True, default=0)
    comment = Column(Text, nullable=True)

    # Relationships
    employee = relationship("Employee", back_populates="attendance_records")


class Holiday(Base):
    """Public / company holidays."""
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    holiday_date = Column(Date, nullable=False, unique=True, index=True)
    holiday_name = Column(String(200), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)  # None = all branches


class LeaveType(Base):
    """Leave type master (Casual, Sick, Annual, etc.)."""
    __tablename__ = "leave_types"

    id = Column(Integer, primary_key=True, index=True)
    leave_type_name = Column(String(100), nullable=False, unique=True)
    max_days = Column(Integer, nullable=True)

    leaves = relationship("Leave", back_populates="leave_type_rel")


class Leave(Base):
    """Employee leave applications."""
    __tablename__ = "leaves"

    id = Column(Integer, primary_key=True, index=True)
    emp_code = Column(String(50), ForeignKey("employees.emp_code"), nullable=False, index=True)
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="Pending")  # Pending/Approved/Rejected
    applied_on = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    employee = relationship("Employee", back_populates="leaves")
    leave_type_rel = relationship("LeaveType", back_populates="leaves")
