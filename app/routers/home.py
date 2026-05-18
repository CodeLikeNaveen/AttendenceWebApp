"""
Home router — serves the validation form and handles employee lookup.
"""

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import attendance_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Render the home validation form with branches loaded from DB."""
    branches = await attendance_service.get_all_branches(db)
    return templates.TemplateResponse("home.html", {
        "request": request,
        "branches": branches,
        "error": None,
    })


@router.post("/", response_class=HTMLResponse)
async def validate_employee(
    request: Request,
    emp_code: str = Form(...),
    emp_name: str = Form(...),
    branch_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Validate employee credentials.
    On success  → redirect to /dashboard/{emp_code}
    On failure  → re-render home with error message
    """
    employee = await attendance_service.validate_employee(db, emp_code, emp_name, branch_id)
    branches = await attendance_service.get_all_branches(db)

    if employee is None:
        return templates.TemplateResponse("home.html", {
            "request": request,
            "branches": branches,
            "error": "No matching active employee found. Please check your details.",
            "prev_emp_code": emp_code,
            "prev_emp_name": emp_name,
            "prev_branch_id": branch_id,
        }, status_code=200)

    # Store emp_code in a cookie for session-like behaviour (no auth needed)
    response = RedirectResponse(url=f"/dashboard/{employee.emp_code}", status_code=303)
    return response
