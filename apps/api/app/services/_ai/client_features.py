"""Fonctionnalites IA orientees client : brief pre-RDV, upsell, recommandations, analyse devis."""

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.integrations.ai.claude_provider import claude_provider
from app.repositories import ai_context_repo
from app.services._ai.context import get_client_cosium_context

logger = get_logger("ai_service")


def pre_rdv_brief(
    db: Session,
    customer_id: int,
    tenant_id: int,
) -> tuple[str, bool]:
    """Genere un brief de preparation avant RDV pour un client.

    Returns:
        (brief_text, context_used) — context_used est False si pas de donnees Cosium.
    """
    cosium_ctx = get_client_cosium_context(db, customer_id, tenant_id)
    if not cosium_ctx:
        return ("", False)

    customer = ai_context_repo.get_customer_by_id(db, customer_id, tenant_id)
    name = f"{customer.first_name} {customer.last_name}" if customer else f"client #{customer_id}"

    system = (
        "Tu es l'assistant de l'opticien. Resume en 5-8 points le dossier client pour preparer un RDV : "
        "dernier equipement et date, evolution des dioptries si notable, PEC en attente, solde impaye, "
        "points de vigilance. Francais clair, pas de jargon technique, max 150 mots."
    )
    question = f"Prepare un brief pour le RDV de {name}."
    result = claude_provider.query_with_usage(question, context=cosium_ctx, system=system)
    logger.info("pre_rdv_brief", tenant_id=tenant_id, customer_id=customer_id)
    return (result.get("text", ""), True)


def upsell_suggestion(
    db: Session,
    customer_id: int,
    tenant_id: int,
) -> tuple[str, bool]:
    """Propose un upsell pertinent base sur l'historique equipement du client."""
    cosium_ctx = get_client_cosium_context(db, customer_id, tenant_id)
    if not cosium_ctx:
        return ("", False)

    customer = ai_context_repo.get_customer_by_id(db, customer_id, tenant_id)
    name = f"{customer.first_name} {customer.last_name}" if customer else f"client #{customer_id}"

    system = (
        "Tu es le conseiller commercial de l'opticien. "
        "A partir de l'historique client (dernier equipement, prescriptions, dioptries), "
        "propose UN seul upsell pertinent et realiste : verres progressifs si addition >= +1.00, "
        "anti-lumiere bleue si profession ecran probable, seconde paire solaire si pas solaire, "
        "lentilles si myopie moderee. "
        "Format : 1 ligne d'accroche + 3 bullets max justifiant. Francais chaleureux, pas de jargon."
    )
    question = f"Suggere un upsell pertinent pour {name}."
    result = claude_provider.query_with_usage(question, context=cosium_ctx, system=system)
    logger.info("upsell_suggestion", tenant_id=tenant_id, customer_id=customer_id)
    return (result.get("text", ""), True)


def product_recommendation(
    db: Session,
    customer_id: int,
    tenant_id: int,
) -> tuple[str, bool]:
    """Recommande des produits adaptes a la derniere prescription du client."""
    cosium_ctx = get_client_cosium_context(db, customer_id, tenant_id)
    if not cosium_ctx:
        return ("", False)

    customer = ai_context_repo.get_customer_by_id(db, customer_id, tenant_id)
    name = f"{customer.first_name} {customer.last_name}" if customer else f"client #{customer_id}"

    system = (
        "Tu es l'expert optique du magasin. A partir des dernieres dioptries du client, "
        "recommande : (1) type de verre ideal (unifocaux / progressifs / occupationnels), "
        "(2) traitements indispensables (anti-reflet, anti-lumiere bleue, durci, photochromique), "
        "(3) materiau adapte (indice >=1.6 si sphere >=+3 ou <=-3, sinon 1.5). "
        "Justifie chaque point par UN parametre precis de la prescription. "
        "Format : liste markdown, max 5 bullets, francais clair."
    )
    question = f"Quel equipement conseiller a {name} ?"
    result = claude_provider.query_with_usage(question, context=cosium_ctx, system=system)
    logger.info("product_recommendation", tenant_id=tenant_id, customer_id=customer_id)
    return (result.get("text", ""), True)


def devis_analysis(
    db: Session,
    devis_id: int,
    tenant_id: int,
) -> tuple[str, list[str]] | None:
    """Analyse la coherence d'un devis vs la prescription client."""
    devis, lignes, customer_id = ai_context_repo.get_devis_with_lines(db, devis_id, tenant_id)
    if not devis:
        return None

    lignes_text = "\n".join(
        f"- {line.designation} x{line.quantite} @ {line.prix_unitaire_ht}EUR HT" for line in lignes
    ) or "(aucune ligne)"

    customer_ctx = ""
    if customer_id:
        customer_ctx = get_client_cosium_context(db, customer_id, tenant_id) or ""

    context = (
        f"DEVIS #{devis.numero} - Total TTC {devis.montant_ttc}EUR\n"
        f"Part Secu {devis.part_secu}EUR, Part mutuelle {devis.part_mutuelle}EUR, "
        f"Reste a charge {devis.reste_a_charge}EUR\n"
        f"Lignes:\n{lignes_text}\n"
        f"\n--- HISTORIQUE CLIENT ---\n{customer_ctx}" if customer_ctx else ""
    )

    system = (
        "Tu es l'assistant qualite de l'opticien. Analyse le devis en 4-5 bullets : "
        "1) Coherence prescription vs verres, 2) Options manquantes (traitement, anti-reflet), "
        "3) Prix par rapport au marche, 4) Points de vigilance pour le client. "
        "Termine par une liste courte de WARNINGS si incoherence grave. Francais professionnel."
    )
    question = f"Analyse le devis #{devis.numero}."
    result = claude_provider.query_with_usage(question, context=context, system=system)
    response_text = result.get("text", "")

    warnings: list[str] = [
        line.strip()
        for line in response_text.split("\n")
        if line.strip().lower().startswith(("warning:", "attention:", "alerte:"))
    ]

    logger.info("devis_analysis", tenant_id=tenant_id, devis_id=devis_id)
    return (response_text, warnings)
