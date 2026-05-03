# Webhooks HTTP sortants — guide integration

> Feature livree 2026-05-02 (commit `07ab6d3`).
> Page admin : `/admin/webhooks`. API : `/api/v1/webhooks/*`.

## Vue d'ensemble

OptiFlow notifie vos systemes tiers en temps reel via HTTP POST quand un
evenement metier se produit (client cree, facture emise, devis signe, etc.).

Pattern : **webhook signe HMAC-SHA256, retry borne, idempotence par event_id**.

## Flux

```
       OptiFlow                    Tiers
   +-------------+            +------------+
   |   Service   | --emit--> | Subscription |
   +-------------+            |    (URL)    |
         |                    +-------------+
         v                          ^
   +-----------+                    |
   | Worker    | --POST signed-----+
   | Celery    |   (5 retries)
   +-----------+
```

1. Un service metier emet un event (`facture.created`)
2. `webhook_service.emit_webhook_event` cree une `WebhookDelivery` par
   subscription active du tenant ecoutant cet event_type
3. Celery worker `deliver_webhook` POST sur `subscription.url` avec
   header `X-Webhook-Signature-256`
4. Sur 2xx -> `status=success`, sur erreur -> retry programme avec
   backoff [30s, 2m, 15m, 1h, 6h], puis `status=failed` apres 5 tentatives

## Event types disponibles (14)

| Event | Quand ? | Payload |
|---|---|---|
| `client.created` | Creation client manuelle ou import | ClientResponse |
| `client.updated` | Modification client | ClientResponse |
| `client.merged` | Fusion 2 doublons | (a venir) |
| `client.deleted` | Soft-delete client | `{client_id, force}` |
| `facture.created` | Generation depuis devis signe | FactureResponse |
| `facture.avoir_created` | Avoir total ou partiel emis | FactureResponse + `original_facture_id` |
| `facture.deleted` | (reserve, pas encore emis) | — |
| `devis.created` | Devis cree (statut brouillon) | DevisResponse |
| `devis.signed` | Devis signe par client | DevisResponse |
| `devis.refused` | Devis refuse | DevisResponse |
| `pec.submitted` | (reserve) | — |
| `pec.accepted` | (reserve) | — |
| `pec.refused` | (reserve) | — |
| `payment.received` | (reserve) | — |
| `campaign.sent` | (reserve) | — |

`GET /api/v1/webhooks/events` retourne la liste actuelle (source de
verite : `app.domain.schemas.webhook.ALLOWED_EVENT_TYPES`).

## Configuration cote tenant (UI)

Dashboard `/admin/webhooks` :

1. Cliquer **Nouvelle subscription**
2. Nom, URL HTTPS, description (optionnel)
3. Cocher les event_types ecoutes (multi-select)
4. **Le secret HMAC est genere et affiche UNE SEULE FOIS** — copier puis stocker chez le destinataire
5. Apres creation, le secret n'est plus affiche que masque (`abcd*****`)

Operations possibles :
- Toggle actif/inactif
- Supprimer (cascade les deliveries)
- Voir 20 dernieres deliveries (refresh 5s)
- Replay une delivery `failed` (admin/manager)

## Format du payload

Chaque delivery POST envoie ce JSON :

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "facture.created",
  "tenant_id": 12,
  "occurred_at": "2026-05-02T14:30:00.123456Z",
  "data": {
    "id": 7,
    "numero": "F-2026-0042",
    "tenant_id": 12,
    "case_id": 5,
    "devis_id": 3,
    "montant_ht": 250.00,
    "tva": 50.00,
    "montant_ttc": 300.00,
    "status": "facturee",
    "created_at": "2026-05-02T14:30:00Z"
  }
}
```

- `event_id` : UUID v4, **cle d'idempotence** cote consommateur. Si
  recu 2 fois (rejeu), dedupliquer.
- `occurred_at` : ISO 8601 UTC avec suffixe `Z`
- `data` : objet metier serialise (schema depend de event_type)

## Headers HTTP

```
Content-Type: application/json
User-Agent: OptiFlow-Webhooks/1.0
X-Webhook-Signature-256: sha256=<hex digest>
X-Webhook-Event: facture.created
X-Webhook-Event-Id: 550e8400-...
X-Webhook-Delivery-Id: 42
X-Webhook-Timestamp: 1714660200
```

## Verification de la signature (CRITIQUE)

Le serveur signe le body brut (bytes) avec votre secret en HMAC-SHA256.
**Verifier la signature avant de traiter le payload** pour rejeter les
requetes forgees.

### Python (FastAPI / Flask)

```python
import hashlib
import hmac

WEBHOOK_SECRET = "le-secret-affiche-une-fois"  # depuis votre stockage securise

def verify_webhook(body: bytes, signature_header: str) -> bool:
    """Verifie X-Webhook-Signature-256 == sha256=<hex(hmac(secret, body))>"""
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    received = signature_header[len("sha256="):]
    return hmac.compare_digest(expected, received)


# FastAPI handler
@app.post("/optiflow-webhook")
async def receive(request: Request):
    body = await request.body()
    sig = request.headers.get("x-webhook-signature-256", "")
    if not verify_webhook(body, sig):
        raise HTTPException(403, "invalid signature")

    payload = json.loads(body)
    # Idempotence
    if seen_event_id(payload["event_id"]):
        return {"status": "duplicate"}
    process_event(payload)
    return {"status": "ok"}
```

### Node.js (Express)

```js
const crypto = require("crypto");
const WEBHOOK_SECRET = process.env.OPTIFLOW_WEBHOOK_SECRET;

function verifyWebhook(rawBody, signatureHeader) {
  if (!signatureHeader.startsWith("sha256=")) return false;
  const expected = crypto
    .createHmac("sha256", WEBHOOK_SECRET)
    .update(rawBody)
    .digest("hex");
  const received = signatureHeader.slice("sha256=".length);
  // constant-time compare
  return crypto.timingSafeEqual(
    Buffer.from(expected),
    Buffer.from(received),
  );
}

app.post(
  "/optiflow-webhook",
  express.raw({ type: "application/json" }),
  (req, res) => {
    if (!verifyWebhook(req.body, req.get("x-webhook-signature-256") || "")) {
      return res.sendStatus(403);
    }
    const payload = JSON.parse(req.body.toString());
    // ...
    res.json({ status: "ok" });
  },
);
```

### PHP

```php
function verifyWebhook(string $body, string $signatureHeader): bool {
    if (!str_starts_with($signatureHeader, 'sha256=')) return false;
    $expected = hash_hmac('sha256', $body, $_ENV['OPTIFLOW_WEBHOOK_SECRET']);
    $received = substr($signatureHeader, 7);
    return hash_equals($expected, $received);
}

$body = file_get_contents('php://input');
$sig = $_SERVER['HTTP_X_WEBHOOK_SIGNATURE_256'] ?? '';
if (!verifyWebhook($body, $sig)) {
    http_response_code(403);
    exit;
}
$payload = json_decode($body, true);
```

## Strategie de retry

| Tentative | Delai apres echec precedent |
|---|---|
| 1 | immediat (a la creation de la delivery) |
| 2 | +30s |
| 3 | +2m |
| 4 | +15m |
| 5 | +1h |
| (final) | +6h |

Apres 5 echecs, status passe a `failed`. Vous pouvez **rejouer
manuellement** depuis `/admin/webhooks` (bouton "Rejouer" sur les
deliveries failed) — admin/manager seulement.

Codes consideres "echec" :
- HTTP 4xx (sauf 401/403/404/410 qui sont retries — votre endpoint
  pourrait etre temporairement indispo)
- HTTP 5xx
- Timeout (10s)
- Erreur reseau

Codes 2xx = success immediat, retries arretes.

## Idempotence

Votre endpoint **DOIT** etre idempotent : recevoir 2 fois le meme
`event_id` ne doit pas creer 2 effets de bord.

Strategie recommandee : table `processed_events(event_id PK, processed_at)`,
verifier au debut du handler.

```sql
INSERT INTO processed_events (event_id, processed_at)
VALUES ($1, now())
ON CONFLICT (event_id) DO NOTHING
RETURNING 1;
-- Si rien retourne : event_id deja traite, ignorer.
```

## Securite / best practices

- **HTTPS uniquement** : la signature ne protege pas contre la lecture
  du payload, seulement l'authenticite. Si vous transferez des
  donnees PII, exigez TLS (URL `https://` cote subscription).
- **Stockez le secret comme un mot de passe** : JAMAIS commit en clair,
  utilisez vault / env / KMS.
- **Rotation** : si le secret fuit, supprimez la subscription et recreez
  la (nouveau secret genere). Aucune downtime grace au replay manuel.
- **Whitelist IP** : actuellement les webhooks partent du VPS unique
  `187.124.217.73`. Si vous voulez restreindre votre endpoint, autoriser
  seulement cette IP (a confirmer avec votre admin).
- **Rate-limit cote endpoint** : 5 retries x N subscriptions x M tenants
  peut faire des pics. Cap a quelques req/s par tenant.

## Troubleshooting

**Toutes les deliveries en `retrying` puis `failed`** :
- Verifier que `subscription.url` est joignable (`curl -X POST ...`)
- Verifier les logs cote endpoint : 403 = signature invalide,
  500 = exception cote consommateur
- Tester manuellement avec la signature : voir snippet Python ci-dessus

**Signature invalide (403 cote consommateur)** :
- Le body doit etre lu **brut** (bytes), pas reserialise
- Express : utiliser `express.raw()`, pas `express.json()`
- FastAPI : `await request.body()`, pas `await request.json()`
- Verifier que le secret stocke = secret affiche a la creation
  (case-sensitive, sans whitespace)

**Deliveries en `pending` qui ne progressent pas** :
- Verifier que le worker Celery tourne :
  `docker compose ps worker` → `Up healthy`
- Verifier que Redis est joignable :
  `docker compose exec redis redis-cli ping` → `PONG`

**Latence elevee** :
- Le worker fait du sequentiel. Pour gros tenants, `--concurrency=4`
  sur le worker Celery (deja le cas en prod)
- Les retries longue distance (1h, 6h) ne bloquent pas les autres
  deliveries (apply_async + countdown, pas blocking sleep)

## Limites V1

- Pas de signature de timestamp (replay-attack window infini). Si critique,
  utilisez `X-Webhook-Timestamp` header + verif `now - timestamp < 5min`.
- Pas de chiffrement payload (signature = integrite + authenticite, pas
  confidentialite). HTTPS gere ca au transport.
- Pas de filtrage par valeur dans l'event (ex: ne notifier que si
  `montant_ttc > 1000`). A configurer cote consommateur.
- Pas de webhook test/ping endpoint pour valider une URL. A faire
  manuellement avec curl + signature.

## Liens

- API : `app/api/routers/webhooks.py`
- Service : `app/services/webhook_service.py`
- Worker : `app/tasks/webhook_tasks.py`
- Schemas : `app/domain/schemas/webhook.py`
- Tests : `tests/test_webhook_*.py` (28 tests)
