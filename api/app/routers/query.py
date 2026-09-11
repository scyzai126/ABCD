"""The Query/Download page's backend.

`POST /query` takes a QuerySpec directly; the GET endpoints build the same object
from query parameters. A future natural-language mode translates a question into a
QuerySpec and posts it here -- it gains no SQL surface of its own, and the same
registry allowlist and Pydantic validation apply.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from .. import execute
from ..deps import filter_params, validation_detail
from ..models import Filters, QueryResult, QuerySpec, SortSpec

router = APIRouter(prefix="/query", tags=["query"])

DELIMITERS = {"csv": ",", "tsv": "\t"}
MEDIA_TYPES = {"csv": "text/csv", "tsv": "text/tab-separated-values"}


@router.post("", response_model=QueryResult)
async def post_query(spec: QuerySpec):
    """Run a fully-specified query. The validated shape the UI and any future
    natural-language layer both submit."""
    return await execute.run(spec)


@router.get("", response_model=QueryResult)
async def get_query(
    measure: str = Query("summary"),
    grain: str = Query("sample"),
    sort: Optional[str] = Query(None),
    descending: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=5000),
    filters: Filters = Depends(filter_params),
):
    """Preview a query. Same parameters as the export, so what you see is what you get."""
    return await execute.run(_spec(measure, grain, sort, descending, page, page_size, filters))


@router.get("/export")
async def export(
    measure: str = Query("summary"),
    grain: str = Query("sample"),
    format: str = Query("csv", pattern="^(csv|tsv)$"),
    sort: Optional[str] = Query(None),
    descending: bool = Query(True),
    filters: Filters = Depends(filter_params),
):
    """Download the full, unpaginated result.

    Every row is tagged with its study name, per the decks' data-standardization
    requirement, and the file opens with comment lines recording the filters used
    and any column whose value is not exact.
    """
    spec = _spec(measure, grain, sort, descending, 1, 5000, filters)
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f"abcd-{spec.measure}-{spec.grain}-{stamp}.{format}"
    return StreamingResponse(
        execute.stream_delimited(spec, DELIMITERS[format]),
        media_type=MEDIA_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _spec(
    measure: str,
    grain: str,
    sort: Optional[str],
    descending: bool,
    page: int,
    page_size: int,
    filters: Filters,
) -> QuerySpec:
    try:
        return QuerySpec(
            measure=measure,
            grain=grain,
            filters=filters,
            sort=SortSpec(column=sort, descending=descending) if sort else None,
            page=page,
            page_size=page_size,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=validation_detail(exc))
