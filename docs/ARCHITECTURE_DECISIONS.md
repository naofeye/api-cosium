# Decisions d'architecture — OptiFlow AI

## Pourquoi user_repo n'a pas de tenant_id

Le `user_repo` (get_user_by_email, get_user_by_id) ne filtre PAS par tenant_id.
Un utilisateur peut appartenir a plusieurs tenants (via `tenant_users`).
L'authentification est globale, le filtrage par tenant se fait dans `TenantContext` apres le login.

## Pourquoi /admin/health est public

L'endpoint `GET /api/v1/admin/health` est accessible sans auth.
Il est utilise par les load balancers et les health checks Docker pour verifier que l'API est operationnelle.
Il ne retourne aucune donnee sensible (seulement le statut des services).

## Pourquoi /billing/webhook n'a pas d'auth JWT

L'endpoint `POST /api/v1/billing/webhook` recoit les webhooks Stripe.
L'authentification se fait via la signature Stripe (STRIPE_WEBHOOK_SECRET), pas via JWT.
C'est le pattern standard recommande par Stripe.

## Pourquoi les cookies sont httpOnly + header fallback

Les tokens JWT sont stockes dans des cookies httpOnly (securite XSS).
Le header `Authorization: Bearer` est supporte en fallback pour :
- Swagger UI (qui ne peut pas envoyer de cookies cross-origin)
- Les tests automatises (pytest)
- Les clients API tiers

## Pourquoi les transitions de statut sont hardcodees

Les dictionnaires VALID_TRANSITIONS (devis, PEC) sont definis dans les services, pas en BDD.
Raisons : simplicite, pas de requete BDD supplementaire, facilement testable.
Si les workflows deviennent dynamiques (configurables par tenant), migrer vers une table `status_workflows`.

## Pourquoi sync_service.py a ete supprime

`sync_service.py` etait l'ancien service de synchronisation Cosium (appel direct).
Il a ete remplace par `erp_sync_service.py` qui utilise l'abstraction `ERPConnector`.
Supprime en TODO V3 car 0% de couverture et 0 imports.
