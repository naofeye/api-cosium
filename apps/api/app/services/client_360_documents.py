"""Client 360 — Documents, prescriptions, equipment, OCR, calendar data."""

import json

from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.client_360 import (
    CorrectionActuelle,
    CosiumCalendarSummary,
    CosiumPaymentSummary,
    CosiumPrescriptionSummary,
    EquipmentItem,
    OcrDataSummary,
    OcrDocumentCount,
    OcrInconsistency,
    OcrMutuelleData,
)
from app.models.cosium_data import CosiumDocument, CosiumPayment, CosiumPrescription
from app.models.cosium_reference import CosiumCalendarEvent, CosiumCustomerTag
from app.models.document_extraction import DocumentExtraction

logger = get_logger("client_360_documents")


def build_prescriptions(
    db: Session,
    tenant_id: int,
    client_id: int,
    cosium_id: str | int | None,
) -> tuple[list[CosiumPrescriptionSummary], list]:
    """Fetch and format prescriptions. Returns (summaries, raw_rows)."""
    rx_query = select(CosiumPrescription).where(
        CosiumPrescription.tenant_id == tenant_id,
    )
    if cosium_id:
        rx_query = rx_query.where(
            (CosiumPrescription.customer_id == client_id)
            | (CosiumPrescription.customer_cosium_id == int(cosium_id))
        )
    else:
        rx_query = rx_query.where(CosiumPrescription.customer_id == client_id)

    prescriptions_raw = db.scalars(
        rx_query.order_by(CosiumPrescription.file_date.desc().nullslast()).limit(20)
    ).all()

    prescriptions = [
        CosiumPrescriptionSummary(
            id=rx.id, cosium_id=rx.cosium_id,
            prescription_date=rx.prescription_date, prescriber_name=rx.prescriber_name,
            sphere_right=rx.sphere_right, cylinder_right=rx.cylinder_right,
            axis_right=rx.axis_right, addition_right=rx.addition_right,
            sphere_left=rx.sphere_left, cylinder_left=rx.cylinder_left,
            axis_left=rx.axis_left, addition_left=rx.addition_left,
            spectacles_json=rx.spectacles_json,
        )
        for rx in prescriptions_raw
    ]
    return prescriptions, list(prescriptions_raw)


def build_correction_actuelle(
    prescriptions_raw: list,
) -> CorrectionActuelle | None:
    """Extract latest correction from raw prescriptions."""
    if not prescriptions_raw:
        return None
    latest = prescriptions_raw[0]
    return CorrectionActuelle(
        prescription_date=latest.prescription_date, prescriber_name=latest.prescriber_name,
        sphere_right=latest.sphere_right, cylinder_right=latest.cylinder_right,
        axis_right=latest.axis_right, addition_right=latest.addition_right,
        sphere_left=latest.sphere_left, cylinder_left=latest.cylinder_left,
        axis_left=latest.axis_left, addition_left=latest.addition_left,
    )


def build_equipments(prescriptions_raw: list) -> list[EquipmentItem]:
    """Extract equipment items from spectacles_json in prescriptions."""
    equipments: list[EquipmentItem] = []
    for rx in prescriptions_raw:
        if not rx.spectacles_json:
            continue
        try:
            specs = json.loads(rx.spectacles_json)
            items = specs if isinstance(specs, list) else [specs] if isinstance(specs, dict) else []
            for spec in items:
                equipments.append(EquipmentItem(
                    prescription_id=rx.id, prescription_date=rx.prescription_date,
                    label=spec.get("label", spec.get("name", "")),
                    brand=spec.get("brand", spec.get("marque", "")),
                    type=spec.get("type", spec.get("famille", "")),
                ))
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("malformed_spectacles_json", prescription_id=rx.id, error=str(exc))
    return equipments


def build_cosium_payments(
    db: Session, tenant_id: int, invoice_cosium_ids: list,
) -> list[CosiumPaymentSummary]:
    """Fetch Cosium payments linked to given invoice cosium IDs."""
    if not invoice_cosium_ids:
        return []
    payments_raw = db.scalars(
        select(CosiumPayment).where(
            CosiumPayment.tenant_id == tenant_id,
            CosiumPayment.invoice_cosium_id.in_(invoice_cosium_ids),
        ).order_by(CosiumPayment.due_date.desc().nullslast()).limit(100)
    ).all()
    return [
        CosiumPaymentSummary(
            id=p.id, cosium_id=p.cosium_id, amount=p.amount, type=p.type,
            due_date=str(p.due_date) if p.due_date else None,
            issuer_name=p.issuer_name, bank=p.bank, site_name=p.site_name,
            payment_number=p.payment_number, invoice_cosium_id=p.invoice_cosium_id,
        )
        for p in payments_raw
    ]


def build_calendar_events(
    db: Session,
    tenant_id: int,
    client_full_name: str,
    cosium_id: str | int | None,
) -> tuple[list[CosiumCalendarSummary], list]:
    """Fetch calendar events. Returns (summaries, raw_rows)."""
    cal_query = select(CosiumCalendarEvent).where(
        CosiumCalendarEvent.tenant_id == tenant_id,
    )
    name_upper = client_full_name.upper()
    if cosium_id:
        cal_query = cal_query.where(
            (sa_func.upper(CosiumCalendarEvent.customer_fullname).contains(name_upper))
            | (CosiumCalendarEvent.customer_number == str(cosium_id))
        )
    else:
        cal_query = cal_query.where(
            sa_func.upper(CosiumCalendarEvent.customer_fullname).contains(name_upper)
        )
    cal_query = cal_query.order_by(
        CosiumCalendarEvent.start_date.desc().nullslast()
    ).limit(30)
    calendar_raw = db.scalars(cal_query).all()

    calendar_events = [
        CosiumCalendarSummary(
            id=ev.id, cosium_id=ev.cosium_id,
            start_date=str(ev.start_date) if ev.start_date else None,
            end_date=str(ev.end_date) if ev.end_date else None,
            subject=ev.subject, category_name=ev.category_name,
            category_color=ev.category_color, status=ev.status,
            canceled=ev.canceled, missed=ev.missed,
            observation=ev.observation, site_name=ev.site_name,
        )
        for ev in calendar_raw
    ]
    return calendar_events, list(calendar_raw)


def get_last_visit_date(
    calendar_raw: list,
    cosium_invoices_raw: list,
) -> str | None:
    """Determine last visit date from calendar or invoices."""
    for ev in calendar_raw:
        if not ev.canceled and ev.start_date:
            return str(ev.start_date)
    for ci in cosium_invoices_raw:
        if ci.invoice_date:
            return str(ci.invoice_date)
    return None


def get_customer_tags(
    db: Session,
    tenant_id: int,
    cosium_id: str | int | None,
) -> list[str]:
    """Fetch customer tags from Cosium reference."""
    if not cosium_id:
        return []
    tag_rows = db.scalars(
        select(CosiumCustomerTag.tag_code).where(
            CosiumCustomerTag.tenant_id == tenant_id,
            CosiumCustomerTag.customer_cosium_id == str(cosium_id),
        )
    ).all()
    return list(tag_rows)


def build_ocr_data(
    db: Session,
    tenant_id: int,
    client_id: int,
    cosium_id: str | int | None,
    prescriptions_raw: list,
) -> OcrDataSummary | None:
    """Build OCR extraction summary for a client."""
    if not cosium_id:
        return None

    cosium_doc_join = (
        (CosiumDocument.cosium_document_id == DocumentExtraction.cosium_document_id)
        & (CosiumDocument.tenant_id == DocumentExtraction.tenant_id)
    )
    cid = int(cosium_id)

    type_counts = db.execute(
        select(DocumentExtraction.document_type, sa_func.count())
        .join(CosiumDocument, cosium_doc_join)
        .where(
            DocumentExtraction.tenant_id == tenant_id,
            CosiumDocument.customer_cosium_id == cid,
            DocumentExtraction.document_type.isnot(None),
        ).group_by(DocumentExtraction.document_type)
    ).all()

    if not type_counts:
        return None

    extraction_counts = [OcrDocumentCount(document_type=r[0], count=r[1]) for r in type_counts]
    total_extracted = sum(r[1] for r in type_counts)

    # Latest attestation mutuelle
    latest_attestation: OcrMutuelleData | None = None
    att = db.scalars(
        select(DocumentExtraction).join(CosiumDocument, cosium_doc_join).where(
            DocumentExtraction.tenant_id == tenant_id,
            DocumentExtraction.document_type.in_(["attestation_mutuelle", "carte_mutuelle"]),
            CosiumDocument.customer_cosium_id == cid,
        ).order_by(DocumentExtraction.extracted_at.desc()).limit(1)
    ).first()
    if att and att.structured_data:
        try:
            sdata = json.loads(att.structured_data)
            if isinstance(sdata, dict):
                latest_attestation = OcrMutuelleData(
                    nom_mutuelle=sdata.get("nom_mutuelle") or sdata.get("mutuelle"),
                    numero_adherent=sdata.get("numero_adherent") or sdata.get("num_adherent"),
                    code_organisme=sdata.get("code_organisme") or sdata.get("code_amc"),
                    source_document_type=att.document_type,
                    extracted_at=str(att.extracted_at) if att.extracted_at else None,
                )
        except (json.JSONDecodeError, TypeError):
            pass

    # Inconsistencies between OCR and Cosium
    inconsistencies: list[OcrInconsistency] = []
    ocr_ord = db.scalars(
        select(DocumentExtraction).join(CosiumDocument, cosium_doc_join).where(
            DocumentExtraction.tenant_id == tenant_id,
            DocumentExtraction.document_type == "ordonnance",
            CosiumDocument.customer_cosium_id == cid,
            DocumentExtraction.structured_data.isnot(None),
        ).order_by(DocumentExtraction.extracted_at.desc()).limit(1)
    ).first()
    if ocr_ord and prescriptions_raw:
        try:
            ocr_rx = json.loads(ocr_ord.structured_data)
            if isinstance(ocr_rx, dict):
                ocr_presc = ocr_rx.get("prescripteur") or ocr_rx.get("medecin") or ""
                cos_presc = prescriptions_raw[0].prescriber_name or ""
                if (
                    ocr_presc and cos_presc
                    and ocr_presc.upper().strip() not in cos_presc.upper()
                    and cos_presc.upper().strip() not in ocr_presc.upper()
                ):
                    inconsistencies.append(OcrInconsistency(
                        field="prescripteur", ocr_value=ocr_presc,
                        cosium_value=cos_presc,
                        message="Le prescripteur OCR ne correspond pas a celui de Cosium",
                    ))
        except (json.JSONDecodeError, TypeError):
            pass

    return OcrDataSummary(
        extraction_counts=extraction_counts,
        total_extracted=total_extracted,
        latest_attestation_mutuelle=latest_attestation,
        inconsistencies=inconsistencies,
    )
