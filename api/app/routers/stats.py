"""The statistics cube: one endpoint per measure, any grain."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import ValidationError

from .. import execute
from ..deps import filter_params, validation_detail
from ..models import Filters, QueryResult, QuerySpec, SortSpec
from ..registry import MEASURES

router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("/{measure}", response_model=QueryResult)
async def get_stats(
    measure: str = Path(description=f"One of: {', '.join(MEASURES)}"),
    grain: str = Query("sample", description="study, subject or sample."),
    sort: Optional[str] = Query(None, description="Column to sort by."),
    descending: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=5000),
    filters: Filters = Depends(filter_params),
):
    """Read one face of the cube.

    `provenance` in the response says, per column, whether the value is read from a
    stored aggregate (`exact`), summed up from the sample grain (`aggregated`),
    count-weighted (`approximate`), absent from this dataset (`empty`), or not
    recoverable from pre-aggregated data under the active filter (`unavailable`).
    """
    try:
        spec = QuerySpec(
            measure=measure,
            grain=grain,
            filters=filters,
            sort=SortSpec(column=sort, descending=descending) if sort else None,
            page=page,
            page_size=page_size,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=validation_detail(exc))
    return await execute.run(spec)
