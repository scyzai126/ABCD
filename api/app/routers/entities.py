"""Study / subject / sample listings.

These read the `ui.*` overview views, which already carry the denormalized
study -> subject -> sample breadcrumb and the matching summary counts.
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from .. import db

router = APIRouter(tags=["entities"])


@router.get("/studies")
async def list_studies():
    rows = await db.fetch("SELECT * FROM ui.study_overview_view ORDER BY study_id")
    return [dict(r) for r in rows]


@router.get("/studies/{study_id}")
async def get_study(study_id: int):
    row = await db.fetchrow(
        "SELECT * FROM ui.study_overview_view WHERE study_id = $1", study_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"no study {study_id}")
    return dict(row)


@router.get("/subjects")
async def list_subjects(
    study_id: Optional[List[int]] = Query(None),
):
    rows = await db.fetch(
        """
        SELECT * FROM ui.subject_overview_view
        WHERE $1::int[] IS NULL OR study_id = ANY($1)
        ORDER BY subject_id
        """,
        study_id,
    )
    return [dict(r) for r in rows]


@router.get("/subjects/{subject_id}")
async def get_subject(subject_id: int):
    row = await db.fetchrow(
        "SELECT * FROM ui.subject_overview_view WHERE subject_id = $1", subject_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"no subject {subject_id}")
    return dict(row)


@router.get("/samples")
async def list_samples(
    study_id: Optional[List[int]] = Query(None),
    subject_id: Optional[List[int]] = Query(None),
):
    rows = await db.fetch(
        """
        SELECT * FROM ui.sample_overview_view
        WHERE ($1::int[] IS NULL OR study_id = ANY($1))
          AND ($2::int[] IS NULL OR subject_id = ANY($2))
        ORDER BY sample_id
        """,
        study_id,
        subject_id,
    )
    return [dict(r) for r in rows]


@router.get("/samples/{sample_id}")
async def get_sample(sample_id: int):
    row = await db.fetchrow(
        "SELECT * FROM ui.sample_overview_view WHERE sample_id = $1", sample_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"no sample {sample_id}")
    return dict(row)
