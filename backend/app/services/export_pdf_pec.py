"""PEC preparation PDF exports."""

import io
from datetime import UTC, datetime

from reportlab.lib import colors as rl_colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.core.logging import log_operation
from app.services.export_pdf_base import (
    create_pdf_doc,
    fmt_money,
    generated_timestamp,
    logger,
    make_footer_style,
    make_section_style,
    make_title_style,
    section_table_style,
)

_SEVERITY_COLORS = {"error": "#DC2626", "warning": "#D97706"}


def _severity_color(sev: str) -> rl_colors.Color:
    return rl_colors.HexColor(_SEVERITY_COLORS.get(sev, "#2563EB"))


def _field_row(label: str, field: dict | None) -> list[str]:
    """Build a table row from a consolidated field dict."""
    if not field:
        return [label, "-", "-", "-"]
    value = str(field.get("value", "-") or "-")
    source = field.get("source_label", field.get("source", "-"))
    confidence = field.get("confidence")
    conf_str = f"{confidence * 100:.0f} %" if confidence is not None else "-"
    return [label, value, str(source), conf_str]

@log_operation("export_pec_preparation_pdf")
def export_pec_preparation_pdf(
    db: Session,
    tenant_id: int,
    preparation_id: int,
) -> bytes:
    """Generate a professional PDF of a PEC preparation worksheet."""
    from app.services import pec_preparation_service

    prep = pec_preparation_service.get_preparation(db, tenant_id, preparation_id)

    output = io.BytesIO()
    doc = create_pdf_doc(output, bottomMargin=20 * mm)

    styles = getSampleStyleSheet()
    elements: list = []

    title_style = make_title_style("PecTitle", font_size=16)
    sec_style = make_section_style("PecSection")
    sec_style.fontSize, sec_style.spaceAfter, sec_style.spaceBefore = 12, 6, 12
    normal = styles["Normal"]
    small = ParagraphStyle("SmallPec", parent=normal, fontSize=8, textColor=rl_colors.grey)

    subtitle_style = ParagraphStyle(
        "PecSubtitle", parent=styles["Normal"], fontSize=10, alignment=1,
        spaceAfter=6, textColor=rl_colors.grey,
    )

    profile = prep.consolidated_data or {}

    elements.append(Paragraph("Fiche d'assistance PEC — OptiFlow", title_style))
    elements.append(Paragraph(
        f"Generee le {generated_timestamp()} | Score de completude : "
        f"{prep.completude_score:.0f} % | Statut : {prep.status}",
        subtitle_style,
    ))
    elements.append(Spacer(1, 6 * mm))

    # -- 1. Identite du patient --
    _append_identity(elements, profile, sec_style)

    # -- 2. Mutuelle / OCAM --
    _append_mutuelle(elements, profile, sec_style)

    # -- 3. Correction optique --
    _append_correction(elements, profile, sec_style)

    # -- 4. Equipement (devis) --
    _append_equipment(elements, profile, sec_style)

    # -- 5. Synthese financiere --
    _append_financial(elements, profile, sec_style)

    # -- 6. Pieces justificatives --
    _append_documents(elements, db, tenant_id, preparation_id, sec_style, small)

    # -- 7. Alertes et incoherences --
    _append_alerts(elements, profile, sec_style, small)

    # Summary
    elements.append(Spacer(1, 4 * mm))
    summary_text = (
        f"Erreurs : {prep.errors_count} | "
        f"Avertissements : {prep.warnings_count} | "
        f"Champs manquants : {', '.join(profile.get('champs_manquants', [])) or 'aucun'}"
    )
    elements.append(Paragraph(summary_text, ParagraphStyle(
        "Summary", parent=normal, fontSize=9, spaceAfter=8,
    )))

    # Footer
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph(
        "Document genere automatiquement — a verifier avant soumission.",
        make_footer_style("PecFooter"),
    ))

    doc.build(elements)
    output.seek(0)

    logger.info(
        "pec_preparation_pdf_exported",
        tenant_id=tenant_id,
        preparation_id=preparation_id,
    )
    return output.getvalue()


def _append_field_section(
    elements, profile, sec_style, title: str, fields: list[tuple[str, str]],
) -> None:
    """Generic helper to append a labelled field-table section."""
    elements.append(Paragraph(title, sec_style))
    rows = [["Champ", "Valeur", "Source", "Confiance"]]
    for label, key in fields:
        rows.append(_field_row(label, profile.get(key)))
    t = Table(rows, colWidths=[120, 160, 100, 60])
    t.setStyle(section_table_style())
    elements.append(t)
    elements.append(Spacer(1, 4 * mm))


def _append_identity(elements, profile, sec_style):
    _append_field_section(elements, profile, sec_style, "1. Identite du patient", [
        ("Nom", "nom"), ("Prenom", "prenom"),
        ("Date de naissance", "date_naissance"), ("N. Securite sociale", "numero_secu"),
    ])


def _append_mutuelle(elements, profile, sec_style):
    _append_field_section(elements, profile, sec_style, "2. Mutuelle / OCAM", [
        ("Mutuelle", "mutuelle_nom"), ("N. Adherent", "mutuelle_numero_adherent"),
        ("Code organisme", "mutuelle_code_organisme"), ("Beneficiaire", "type_beneficiaire"),
        ("Fin de droits", "date_fin_droits"),
    ])


def _eye_row(profile: dict, eye: str, suffix: str) -> list[str]:
    """Build a correction row for OD or OG."""
    return [eye] + [
        str((profile.get(f"{f}_{suffix}") or {}).get("value", "-"))
        for f in ("sphere", "cylinder", "axis", "addition")
    ]


def _append_correction(elements, profile, sec_style):
    elements.append(Paragraph("3. Correction optique", sec_style))
    corr_header = ["", "Sphere", "Cylindre", "Axe", "Addition"]
    od_row = _eye_row(profile, "OD", "od")
    og_row = _eye_row(profile, "OG", "og")
    corr_table = Table([corr_header, od_row, og_row], colWidths=[40, 80, 80, 60, 80])
    corr_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#2563EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            rl_colors.white, rl_colors.HexColor("#F9FAFB"),
        ]),
    ]))
    elements.append(corr_table)

    prescripteur = profile.get("prescripteur")
    date_ordo = profile.get("date_ordonnance")
    ep = profile.get("ecart_pupillaire")
    extra_rows = []
    if prescripteur:
        extra_rows.append(_field_row("Prescripteur", prescripteur))
    if date_ordo:
        extra_rows.append(_field_row("Date ordonnance", date_ordo))
    if ep:
        extra_rows.append(_field_row("Ecart pupillaire", ep))
    if extra_rows:
        extra_rows.insert(0, ["Champ", "Valeur", "Source", "Confiance"])
        et = Table(extra_rows, colWidths=[120, 160, 100, 60])
        et.setStyle(section_table_style())
        elements.append(Spacer(1, 2 * mm))
        elements.append(et)
    elements.append(Spacer(1, 4 * mm))


def _append_equipment(elements, profile, sec_style):
    elements.append(Paragraph("4. Equipement (lignes devis)", sec_style))
    equip_rows = [["Element", "Valeur", "Source", "Confiance"]]
    monture = profile.get("monture")
    if monture:
        equip_rows.append(_field_row("Monture", monture))
    verres = profile.get("verres", [])
    for i, v in enumerate(verres):
        equip_rows.append(_field_row(f"Verre {i + 1}", v))
    if len(equip_rows) == 1:
        equip_rows.append(["", "Aucun equipement renseigne", "", ""])
    eq_table = Table(equip_rows, colWidths=[120, 160, 100, 60])
    eq_table.setStyle(section_table_style())
    elements.append(eq_table)
    elements.append(Spacer(1, 4 * mm))


def _fin_field(field: dict | None) -> tuple[str, str, str]:
    """Extract formatted (value, source, confidence) from a financial field."""
    if not field:
        return "-", "-", "-"
    val = fmt_money(float(field["value"])) if field.get("value") is not None else "-"
    source = str(field.get("source_label", "-"))
    conf = f"{field['confidence'] * 100:.0f} %" if field.get("confidence") is not None else "-"
    return val, source, conf


def _append_financial(elements, profile, sec_style):
    elements.append(Paragraph("5. Synthese financiere", sec_style))
    fin_rows = [["Poste", "Montant", "Source", "Confiance"]]
    for label, key in [
        ("Total TTC", "montant_ttc"), ("Part Securite sociale", "part_secu"),
        ("Part Mutuelle", "part_mutuelle"), ("Reste a charge", "reste_a_charge"),
    ]:
        val, source, conf = _fin_field(profile.get(key))
        fin_rows.append([label, val, source, conf])
    fin_table = Table(fin_rows, colWidths=[120, 120, 100, 60])
    fin_table.setStyle(section_table_style())
    elements.append(fin_table)
    elements.append(Spacer(1, 4 * mm))


def _append_documents(elements, db, tenant_id, preparation_id, sec_style, small):
    elements.append(Paragraph("6. Pieces justificatives", sec_style))
    from app.services import pec_preparation_service as pps
    try:
        docs = pps.list_documents(db, tenant_id, preparation_id)
        if docs:
            doc_rows = [["Role", "Document ID", "Cosium Doc ID"]]
            for d in docs:
                doc_rows.append([
                    d.document_role,
                    str(d.document_id or "-"),
                    str(d.cosium_document_id or "-"),
                ])
            doc_table = Table(doc_rows, colWidths=[120, 120, 120])
            doc_table.setStyle(section_table_style())
            elements.append(doc_table)
        else:
            elements.append(Paragraph("Aucune piece justificative attachee.", small))
    except Exception:
        elements.append(Paragraph("Impossible de charger les pieces justificatives.", small))
    elements.append(Spacer(1, 4 * mm))


def _append_alerts(elements, profile, sec_style, small):
    elements.append(Paragraph("7. Alertes et incoherences", sec_style))
    alertes = profile.get("alertes", [])
    if alertes:
        alert_rows = [["Severite", "Champ", "Message"]]
        for a in alertes:
            sev = a.get("severity", "info")
            alert_rows.append([sev.upper(), a.get("field", "-"), a.get("message", "-")])
        alert_table = Table(alert_rows, colWidths=[60, 100, 280])
        alert_ts = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#374151")),
            ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
        alert_table.setStyle(alert_ts)
        for i, a in enumerate(alertes, start=1):
            sev = a.get("severity", "info")
            color = _severity_color(sev)
            alert_table.setStyle(TableStyle([
                ("TEXTCOLOR", (0, i), (0, i), color),
                ("FONTNAME", (0, i), (0, i), "Helvetica-Bold"),
            ]))
        elements.append(alert_table)
    else:
        elements.append(Paragraph("Aucune alerte detectee.", small))
    elements.append(Spacer(1, 4 * mm))
