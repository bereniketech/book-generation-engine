"""Chapter lock utilities — readability scoring helpers."""
from __future__ import annotations

import textstat

from app.core.logging import get_logger

log = get_logger(__name__)


def compute_and_store_readability(
    client,
    job_id: str,
    chapter_index: int,
    content: str,
) -> None:
    """Compute Flesch-Kincaid scores and store them in the chapters table."""
    try:
        grade = textstat.flesch_kincaid_grade(content)
        ease = textstat.flesch_reading_ease(content)

        client.table("chapters").update({
            "flesch_kincaid_grade": round(grade, 2),
            "flesch_reading_ease": round(ease, 2),
        }).eq("job_id", job_id).eq("index", chapter_index).execute()

        log.info(
            "chapter.readability.scored",
            job_id=job_id,
            chapter_index=chapter_index,
            flesch_kincaid_grade=round(grade, 2),
            flesch_reading_ease=round(ease, 2),
        )
    except Exception as exc:
        log.warning(
            "chapter.readability.score_failed",
            job_id=job_id,
            chapter_index=chapter_index,
            error=str(exc),
        )
