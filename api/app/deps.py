"""Shared request parsing.

Query parameters deserialize into exactly the same `Filters` model that
`POST /query` accepts as JSON, so there is one validator and one SQL builder behind
both entry points.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, Query
from pydantic import ValidationError

from .models import Filters


def filter_params(
    study_id: Optional[List[int]] = Query(None, description="Restrict to these studies."),
    subject_id: Optional[List[int]] = Query(None, description="Restrict to these subjects."),
    sample_id: Optional[List[int]] = Query(None, description="Restrict to these samples."),
    chain: Optional[List[str]] = Query(None, description="IGH, IGK or IGL."),
    celltype_id: Optional[List[int]] = Query(None, description="Annotated cell type ids."),
    allele_id: Optional[List[int]] = Query(None, description="V/J allele ids."),
    allele_segment: Optional[List[str]] = Query(
        None, description="Derived allele segment, e.g. IGHV, IGKJ."
    ),
    allele_gene: Optional[List[str]] = Query(
        None, description="Derived allele gene, e.g. IGHV1-18."
    ),
    meta: Optional[List[str]] = Query(
        None,
        description=(
            "Entity metadata filter as 'field:value', repeatable. "
            "Example: meta=disease_reported:SLE. Available fields come from "
            "/api/v1/meta/facets -- most are unpopulated in the current dataset."
        ),
    ),
    age_min: Optional[float] = Query(None),
    age_max: Optional[float] = Query(None),
    time_collected_from: Optional[datetime] = Query(None),
    time_collected_to: Optional[datetime] = Query(None),
) -> Filters:
    metadata = {}
    for item in meta or []:
        if ":" not in item:
            raise HTTPException(
                status_code=422,
                detail=f"metadata filter {item!r} must be formatted 'field:value'",
            )
        field_name, value = item.split(":", 1)
        metadata.setdefault(field_name.strip(), []).append(value)

    try:
        return Filters(
            study_id=study_id or [],
            subject_id=subject_id or [],
            sample_id=sample_id or [],
            chain=chain or [],
            celltype_id=celltype_id or [],
            allele_id=allele_id or [],
            allele_segment=allele_segment or [],
            allele_gene=allele_gene or [],
            metadata=metadata,
            age_min=age_min,
            age_max=age_max,
            time_collected_from=time_collected_from,
            time_collected_to=time_collected_to,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=validation_detail(exc))


def validation_detail(exc: ValidationError) -> List[dict]:
    """A JSON-safe 422 body.

    Pydantic's `errors()` embeds the offending input and the original exception
    object; here the input is a `Filters` model, which the JSON encoder cannot
    handle. Location, message and type are what a caller actually needs.
    """
    return [
        {"loc": list(e.get("loc", ())), "msg": e.get("msg", ""), "type": e.get("type", "")}
        for e in exc.errors(include_url=False, include_context=False, include_input=False)
    ]
