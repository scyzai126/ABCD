"""Running a QuerySpec: paginated JSON, and streamed delimited export."""
import csv
import io
from typing import Any, AsyncIterator, Dict, List

from . import db
from .models import Provenance, QueryResult, QuerySpec
from .query import build, output_columns


def _clean(record: Any) -> Dict[str, Any]:
    row = dict(record)
    row.pop("__total", None)
    return row


async def run(spec: QuerySpec) -> QueryResult:
    sql, params, provenance, notes = build(spec, paginate=True)
    records = await db.fetch(sql, *params)
    total = records[0]["__total"] if records else 0
    return QueryResult(
        spec=spec,
        total=total,
        page=spec.page,
        page_size=spec.page_size,
        columns=output_columns(spec),
        rows=[_clean(r) for r in records],
        provenance=provenance,
        notes=notes,
    )


async def stream_delimited(spec: QuerySpec, delimiter: str = ",") -> AsyncIterator[str]:
    """Stream the full, unpaginated result as CSV/TSV.

    Every row carries the study name (and subject/sample names at finer grains) --
    the decks require exported records to be tagged with the study they came from.
    A leading comment line records the filters and provenance so a downloaded file
    can still be interpreted months later.
    """
    sql, params, provenance, notes = build(spec, paginate=False)
    columns = output_columns(spec)

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter, lineterminator="\n")

    def flush() -> str:
        value = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        return value

    header_comment = (
        f"# ABCD export | measure={spec.measure} grain={spec.grain} "
        f"| filters={spec.filters.model_dump_json(exclude_defaults=True)}\n"
    )
    yield header_comment
    approximate = sorted(
        column
        for column, value in provenance.items()
        if value in (Provenance.APPROXIMATE, Provenance.UNAVAILABLE, Provenance.EMPTY)
    )
    if approximate:
        yield f"# non-exact columns: {', '.join(f'{c}={provenance[c].value}' for c in approximate)}\n"
    for note in notes:
        yield f"# note: {note}\n"

    writer.writerow(columns)
    yield flush()

    async with db.pool().acquire() as conn:
        async with conn.transaction():
            async for record in conn.cursor(sql, *params):
                row = _clean(record)
                writer.writerow([row.get(column) for column in columns])
                yield flush()
