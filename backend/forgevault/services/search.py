from sqlalchemy import String, cast, or_, select
from sqlalchemy.orm import Session

from ..models import FileVersion, Record


def search_records(session: Session, query: str, *, limit: int = 50) -> list[tuple[Record, FileVersion | None]]:
    pattern = f"%{query}%"
    records = session.scalars(
        select(Record)
        .outerjoin(FileVersion, FileVersion.record_id == Record.id)
        .where(
            or_(
                Record.internal_record_id.ilike(pattern),
                Record.customer_part_number.ilike(pattern),
                Record.customer_revision.ilike(pattern),
                Record.internal_revision.ilike(pattern),
                FileVersion.filename.ilike(pattern),
                FileVersion.original_source_path.ilike(pattern),
                cast(Record.record_metadata, String).ilike(pattern),
                cast(FileVersion.version_metadata, String).ilike(pattern),
            )
        )
        .distinct()
        .limit(limit)
    ).all()
    results = []
    for record in records:
        latest = session.scalar(select(FileVersion).where(FileVersion.record_id == record.id).order_by(FileVersion.version_number.desc()).limit(1))
        results.append((record, latest))
    return results
