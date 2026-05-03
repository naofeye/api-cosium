"""SSRF guard pour webhooks sortants.

Refuse les URLs vers des destinations internes (loopback, RFC1918, link-local,
metadata cloud, hostnames Docker internes) AVANT d'envoyer la requete HTTP.

Defense-in-depth : appele au moment de la livraison (pas a la creation), pour
bloquer les hostnames qui resolvent a chaud vers des IPs internes (rebind DNS,
hostnames qui changent entre la creation et la livraison).

Cible Codex critique #1 (REVIEW.md 2026-05-03) : la task `deliver_webhook`
faisait `httpx.post(sub.url, ...)` sans valider l'URL. Un tenant pouvait
creer une subscription pointant vers `http://api:8000/admin/...` ou
`http://169.254.169.254/latest/meta-data/...` (AWS IMDS) et utiliser le
worker Celery comme proxy SSRF.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

# Hostnames Docker compose internes du projet — refuses meme si l'IP resolue
# passerait les autres checks. Defense en profondeur. La liste correspond
# aux service names du docker-compose.yml (api, web, worker, beat, postgres,
# redis, minio, mailhog).
_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "ip6-localhost",
        "ip6-loopback",
        "api",
        "web",
        "worker",
        "beat",
        "postgres",
        "redis",
        "minio",
        "mailhog",
    }
)

_ALLOWED_SCHEMES = frozenset({"http", "https"})


class WebhookUrlForbiddenError(ValueError):
    """L'URL pointe vers une destination interdite (interne / metadata cloud)."""


def _ip_is_internal(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    # is_private couvre RFC1918 (10/8, 172.16/12, 192.168/16) + loopback (127/8)
    # + link-local (169.254/16, qui inclut 169.254.169.254 metadata AWS/GCP/
    # Azure) + IPv6 ULA (fc00::/7) + IPv6 loopback (::1) + IPv6 link-local
    # (fe80::/10).
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def assert_url_safe(url: str) -> None:
    """Leve `WebhookUrlForbiddenError` si l'URL pointe vers une cible interne.

    Verifications, dans l'ordre :
        1. scheme http/https uniquement (refuse file://, gopher://, etc.)
        2. hostname present
        3. hostname pas dans la blocklist Docker compose
        4. si hostname est une IP litterale -> refuser si interne
        5. sinon : resolution DNS A/AAAA, *toutes* les IPs doivent etre publiques

    L'option 5 protege contre :
        - hostnames qui resolvent vers RFC1918 (ex. tenant pointe vers son LAN)
        - DNS rebinding partiel (un hostname avec plusieurs A records dont un interne)
        - acces direct aux metadata cloud via hostname custom qui resout
          vers 169.254.169.254
    """
    parsed = urlparse(url)

    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise WebhookUrlForbiddenError(
            f"scheme '{parsed.scheme}' refuse (http/https uniquement)"
        )

    host = (parsed.hostname or "").lower()
    if not host:
        raise WebhookUrlForbiddenError("URL sans hostname")

    if host in _BLOCKED_HOSTNAMES:
        raise WebhookUrlForbiddenError(f"hostname interne refuse : {host}")

    # Si le hostname est deja une IP litterale, valider directement sans DNS.
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None

    if literal is not None:
        if _ip_is_internal(literal):
            raise WebhookUrlForbiddenError(f"IP interne refusee : {host}")
        return

    # Resolution DNS : toutes les IPs resolues doivent etre publiques.
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise WebhookUrlForbiddenError(
            f"hostname non resolvable : {host} ({exc})"
        ) from exc

    seen: set[str] = set()
    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        # IPv6 link-local peut contenir un scope (%eth0). On le retire.
        if "%" in ip_str:
            ip_str = ip_str.split("%", 1)[0]
        if ip_str in seen:
            continue
        seen.add(ip_str)
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if _ip_is_internal(ip):
            raise WebhookUrlForbiddenError(
                f"hostname {host} resolu vers IP interne {ip_str}"
            )
