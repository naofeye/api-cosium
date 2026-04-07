"""Re-classify documents currently tagged as 'autre'.

Usage:
    docker compose exec api python -m scripts.reclassify_documents [--dry-run] [--tenant-id N]

Reads the raw_text from document_extractions where document_type='autre',
applies the enhanced classification rules, and updates matching rows.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from sqlalchemy import select, update

# Ensure app package is importable
sys.path.insert(0, "/app")

from app.db.session import SessionLocal  # noqa: E402
from app.models.document_extraction import DocumentExtraction  # noqa: E402
from app.services.ocr_service import classify_document  # noqa: E402


def reclassify_autre_documents(
    tenant_id: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Re-classify documents currently tagged as 'autre'.

    Returns stats: {reclassified: N, still_autre: N, by_new_type: {...}}
    """
    db = SessionLocal()
    try:
        q = select(DocumentExtraction).where(
            DocumentExtraction.document_type == "autre",
            DocumentExtraction.raw_text.isnot(None),
            DocumentExtraction.raw_text != "",
        )
        if tenant_id is not None:
            q = q.where(DocumentExtraction.tenant_id == tenant_id)

        rows = db.scalars(q).all()

        reclassified = 0
        still_autre = 0
        by_new_type: dict[str, int] = defaultdict(int)

        for row in rows:
            result = classify_document(row.raw_text or "")
            if result.document_type != "autre" and result.confidence >= 0.15:
                by_new_type[result.document_type] += 1
                reclassified += 1
                if not dry_run:
                    db.execute(
                        update(DocumentExtraction)
                        .where(DocumentExtraction.id == row.id)
                        .values(
                            document_type=result.document_type,
                            classification_confidence=result.confidence,
                        )
                    )
            else:
                still_autre += 1

        if not dry_run:
            db.commit()

        stats = {
            "total_processed": len(rows),
            "reclassified": reclassified,
            "still_autre": still_autre,
            "by_new_type": dict(by_new_type),
            "dry_run": dry_run,
        }
        return stats
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-classify 'autre' documents")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--tenant-id", type=int, default=None, help="Limit to a specific tenant")
    args = parser.parse_args()

    print(f"Re-classifying 'autre' documents (dry_run={args.dry_run})...")
    stats = reclassify_autre_documents(tenant_id=args.tenant_id, dry_run=args.dry_run)
    print(f"Total processed: {stats['total_processed']}")
    print(f"Reclassified:    {stats['reclassified']}")
    print(f"Still 'autre':   {stats['still_autre']}")
    print(f"By new type:     {stats['by_new_type']}")
    if stats["dry_run"]:
        print("(DRY RUN - no changes saved)")


if __name__ == "__main__":
    main()
