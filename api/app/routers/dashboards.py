"""The two dashboard pages from the design decks."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import dashboard as dashboard_service
from ..deps import filter_params
from ..models import Dashboard, Filters

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=Dashboard)
async def get_dashboard(
    level: str = Query("project", pattern="^(project|study)$"),
    study_id_scope: Optional[int] = Query(
        None,
        alias="scope_study_id",
        description="Required when level=study. The study the page is about.",
    ),
    filters: Filters = Depends(filter_params),
):
    """KPI tiles and breakdown charts for the project- or study-level dashboard.

    Every filter change re-fetches this one call, which is what makes the decks'
    "dynamically recalculated" aggregate summary work. Each tile and chart carries
    a `provenance` field saying whether its number is read straight from a stored
    aggregate, summed up from a finer grain, count-weighted, or not answerable at
    all from pre-aggregated data.
    """
    if level == "study" and study_id_scope is None:
        raise HTTPException(
            status_code=422, detail="scope_study_id is required when level=study"
        )
    return await dashboard_service.assemble(level, filters, study_id_scope)
