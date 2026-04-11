"""Enrich CosiumPrescription diopter data from OCR ordonnance extractions.

For prescriptions with NULL sphere/cylinder values, check if there's a matching
DocumentExtraction of type "ordonnance" with structured_data containing OD/OG data.
If found, fill in the missing values.

Usage:
    docker compose exec api python -m scripts.enrich_prescriptions_ocr
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Customer, Tenant
from app.models.cosium_data import CosiumDocument, CosiumPrescription
from app.models.document_extraction import DocumentExtraction

BATCH_SIZE = 500


def _parse_float(val: object) -> float | None:
    """Safely parse a float from OCR data."""
    if val is None:
        return None
    try:
        s = str(val).strip().replace(",", ".").replace("+", "")
        if not s or s == "-" or s.lower() in ("null", "none", ""):
            return None
        return float(s)
    except (ValueError, TypeError):
        return None


def _extract_od_og(structured_data: dict) -> dict:
    """Extract OD/OG diopter data from structured OCR data.

    Supports multiple key formats from different OCR parsers.
    Returns dict with sphere_right, cylinder_right, etc.
    """
    result: dict[str, float | None] = {}

    # Try multiple key patterns for OD (right eye)
    od = structured_data.get("OD") or structured_data.get("od") or structured_data.get("oeil_droit") or {}
    if isinstance(od, dict):
        result["sphere_right"] = _parse_float(
            od.get("sphere") or od.get("sph") or od.get("S")
        )
        result["cylinder_right"] = _parse_float(
            od.get("cylindre") or od.get("cyl") or od.get("C") or od.get("cylinder")
        )
        result["axis_right"] = _parse_float(
            od.get("axe") or od.get("axis") or od.get("A")
        )
        result["addition_right"] = _parse_float(
            od.get("addition") or od.get("add") or od.get("ADD")
        )

    # Try multiple key patterns for OG (left eye)
    og = structured_data.get("OG") or structured_data.get("og") or structured_data.get("oeil_gauche") or {}
    if isinstance(og, dict):
        result["sphere_left"] = _parse_float(
            og.get("sphere") or og.get("sph") or og.get("S")
        )
        result["cylinder_left"] = _parse_float(
            og.get("cylindre") or og.get("cyl") or og.get("C") or og.get("cylinder")
        )
        result["axis_left"] = _parse_float(
            og.get("axe") or og.get("axis") or og.get("A")
        )
        result["addition_left"] = _parse_float(
            og.get("addition") or og.get("add") or og.get("ADD")
        )

    # Flat format: sphere_od, sphere_og, etc.
    if not od and not og:
        result["sphere_right"] = _parse_float(
            structured_data.get("sphere_od") or structured_data.get("sph_od")
        )
        result["cylinder_right"] = _parse_float(
            structured_data.get("cylindre_od") or structured_data.get("cyl_od")
        )
        result["axis_right"] = _parse_float(
            structured_data.get("axe_od") or structured_data.get("axis_od")
        )
        result["addition_right"] = _parse_float(
            structured_data.get("addition_od") or structured_data.get("add_od")
        )
        result["sphere_left"] = _parse_float(
            structured_data.get("sphere_og") or structured_data.get("sph_og")
        )
        result["cylinder_left"] = _parse_float(
            structured_data.get("cylindre_og") or structured_data.get("cyl_og")
        )
        result["axis_left"] = _parse_float(
            structured_data.get("axe_og") or structured_data.get("axis_og")
        )
        result["addition_left"] = _parse_float(
            structured_data.get("addition_og") or structured_data.get("add_og")
        )

    return result


def _prescription_needs_enrichment(presc: CosiumPrescription) -> bool:
    """Check if a prescription has missing diopter data that could be enriched."""
    return (
        presc.sphere_right is None
        and presc.sphere_left is None
        and presc.cylinder_right is None
        and presc.cylinder_left is None
    )


def enrich_prescriptions_from_ocr(db: Session, tenant_id: int) -> dict:
    """Enrich incomplete prescriptions using OCR ordonnance data."""
    # Get prescriptions needing enrichment (all sphere/cylinder NULL)
    prescriptions = db.scalars(
        select(CosiumPrescription).where(
            CosiumPrescription.tenant_id == tenant_id,
            CosiumPrescription.sphere_right.is_(None),
            CosiumPrescription.sphere_left.is_(None),
            CosiumPrescription.cylinder_right.is_(None),
            CosiumPrescription.cylinder_left.is_(None),
        )
    ).all()

    enriched = 0
    no_ocr_match = 0
    ocr_no_data = 0
    processed = 0

    for presc in prescriptions:
        # Find matching OCR ordonnance extraction
        # Match by customer_cosium_id if available, otherwise by date proximity
        ocr_extraction = None

        if presc.customer_cosium_id:
            ocr_extraction = db.scalars(
                select(DocumentExtraction).join(
                    CosiumDocument,
                    (CosiumDocument.cosium_document_id == DocumentExtraction.cosium_document_id)
                    & (CosiumDocument.tenant_id == DocumentExtraction.tenant_id),
                ).where(
                    DocumentExtraction.tenant_id == tenant_id,
                    DocumentExtraction.document_type == "ordonnance",
                    DocumentExtraction.structured_data.isnot(None),
                    CosiumDocument.customer_cosium_id == int(presc.customer_cosium_id),
                ).order_by(DocumentExtraction.extracted_at.desc()).limit(1)
            ).first()

        if not ocr_extraction and presc.customer_id:
            # Try via customer_id -> Customer.cosium_id -> CosiumDocument
            customer = db.get(Customer, presc.customer_id)
            if customer and customer.cosium_id:
                ocr_extraction = db.scalars(
                    select(DocumentExtraction).join(
                        CosiumDocument,
                        (CosiumDocument.cosium_document_id == DocumentExtraction.cosium_document_id)
                        & (CosiumDocument.tenant_id == DocumentExtraction.tenant_id),
                    ).where(
                        DocumentExtraction.tenant_id == tenant_id,
                        DocumentExtraction.document_type == "ordonnance",
                        DocumentExtraction.structured_data.isnot(None),
                        CosiumDocument.customer_cosium_id == int(customer.cosium_id),
                    ).order_by(DocumentExtraction.extracted_at.desc()).limit(1)
                ).first()

        if not ocr_extraction:
            no_ocr_match += 1
            processed += 1
            continue

        # Parse structured data
        try:
            sdata = json.loads(ocr_extraction.structured_data)
        except (json.JSONDecodeError, TypeError):
            no_ocr_match += 1
            processed += 1
            continue

        if not isinstance(sdata, dict):
            ocr_no_data += 1
            processed += 1
            continue

        od_og = _extract_od_og(sdata)

        # Only enrich if we actually got some data
        has_data = any(v is not None for v in od_og.values())
        if not has_data:
            ocr_no_data += 1
            processed += 1
            continue

        # Fill in missing values
        updated = False
        for field, value in od_og.items():
            if value is not None and getattr(presc, field) is None:
                setattr(presc, field, value)
                updated = True

        if updated:
            enriched += 1
        else:
            ocr_no_data += 1

        processed += 1
        if processed % BATCH_SIZE == 0:
            db.flush()

    db.commit()
    return {
        "total_incomplete": len(prescriptions),
        "enriched_from_ocr": enriched,
        "no_ocr_match": no_ocr_match,
        "ocr_no_useful_data": ocr_no_data,
    }


def main() -> None:
    db = SessionLocal()
    try:
        tenants = db.scalars(select(Tenant)).all()
        for tenant in tenants:
            print(f"\n=== Tenant: {tenant.name} (id={tenant.id}) ===")
            stats = enrich_prescriptions_from_ocr(db, tenant.id)
            print(f"  Prescription Enrichment: {stats}")
            pct = (
                round(stats["enriched_from_ocr"] / stats["total_incomplete"] * 100, 1)
                if stats["total_incomplete"] > 0
                else 0
            )
            print(f"  Enriched: {stats['enriched_from_ocr']}/{stats['total_incomplete']} ({pct}%)")
        print("\nDone.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
