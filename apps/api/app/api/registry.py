"""Registre central des routers FastAPI.

Extrait de `main.py` pour faciliter la lecture et maintenir une seule
source de vérité pour l'inclusion des routers. À ajouter un nouveau
router : l'importer ci-dessous et l'ajouter à la liste dans
`register_routers()`.
"""

from fastapi import FastAPI

from app.api.routers import (
    action_items,
    admin_health,
    admin_tenant_security,
    admin_users,
    ai,
    ai_usage,
    analytics,
    audit,
    auth,
    banking,
    batch_operations,
    billing,
    cases,
    client_360,
    client_mutuelles,
    clients,
    consents,
    cosium_catalog,
    cosium_commercial,
    cosium_documents,
    cosium_fidelity,
    cosium_invoices,
    cosium_notes,
    cosium_reference,
    cosium_sav,
    cosium_spectacles,
    dashboard,
    devis,
    documents,
    exports,
    extractions,
    factures,
    gdpr,
    marketing,
    metrics,
    notifications,
    ocam_operators,
    onboarding,
    payments,
    pec,
    pec_preparation,
    reconciliation,
    reminders,
    renewals,
    search,
    sse,
    sync,
    web_vitals,
)


def register_routers(app: FastAPI) -> None:
    """Attache tous les routers de l'API sur l'application FastAPI."""
    app.include_router(action_items.router)
    app.include_router(ai.router)
    app.include_router(cosium_documents.router)
    app.include_router(cosium_invoices.router)
    app.include_router(ai_usage.router)
    app.include_router(analytics.router)
    app.include_router(audit.router)
    app.include_router(banking.router)
    app.include_router(billing.router)
    app.include_router(auth.router)
    app.include_router(cases.router)
    app.include_router(client_mutuelles.router)
    app.include_router(clients.router)
    app.include_router(devis.router)
    app.include_router(documents.router)
    app.include_router(extractions.router)
    app.include_router(factures.router)
    app.include_router(notifications.router)
    app.include_router(payments.router)
    app.include_router(pec.router)
    app.include_router(pec_preparation.router)
    app.include_router(reconciliation.router)
    app.include_router(reminders.router)
    app.include_router(renewals.router)
    app.include_router(consents.router)
    app.include_router(marketing.router)
    app.include_router(metrics.router)
    app.include_router(web_vitals.router)
    app.include_router(search.router)
    app.include_router(sync.router)
    app.include_router(exports.router)
    app.include_router(gdpr.router)
    app.include_router(client_360.router)
    app.include_router(admin_health.router)
    app.include_router(admin_tenant_security.router)
    app.include_router(admin_users.router)
    app.include_router(dashboard.router)
    app.include_router(onboarding.router)
    app.include_router(cosium_reference.router)
    app.include_router(cosium_spectacles.router)
    app.include_router(cosium_catalog.router)
    app.include_router(cosium_sav.router)
    app.include_router(cosium_notes.router)
    app.include_router(cosium_fidelity.router)
    app.include_router(cosium_commercial.router)
    app.include_router(ocam_operators.router)
    app.include_router(batch_operations.router)
    app.include_router(sse.router)
