"""Account lockout and login attempt tracking via Redis.

Extracted from auth_service.py to keep files under 300 lines.
"""

from app.core.exceptions import AuthenticationError
from app.core.logging import get_logger

logger = get_logger("auth_lockout")

# Account lockout: max 5 failed attempts, lockout 30 minutes
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 1800


def check_account_lockout(email: str) -> None:
    """Verifie si le compte est bloque apres trop de tentatives echouees."""
    try:
        from app.core.redis_cache import get_redis_client

        r = get_redis_client()
        if r is None:
            return
        key = f"login_attempts:{email}"
        attempts = r.get(key)
        if attempts and int(attempts) >= MAX_LOGIN_ATTEMPTS:
            ttl = r.ttl(key)
            minutes = max(1, (ttl or LOCKOUT_SECONDS) // 60)
            raise AuthenticationError(
                f"Compte temporairement bloque apres {MAX_LOGIN_ATTEMPTS} tentatives echouees. "
                f"Reessayez dans {minutes} minutes."
            )
    except AuthenticationError:
        raise
    except Exception as exc:
        logger.debug("auth_lockout_check_failed", email=email, error=str(exc))


def record_failed_login(email: str) -> None:
    """Enregistre une tentative de login echouee."""
    try:
        from app.core.redis_cache import get_redis_client

        r = get_redis_client()
        if r is None:
            return
        key = f"login_attempts:{email}"
        current = r.incr(key)
        if current == 1:
            r.expire(key, LOCKOUT_SECONDS)
    except Exception as exc:
        logger.warning("record_failed_login_redis_error", error=str(exc))


def clear_login_attempts(email: str) -> None:
    """Reinitialise les tentatives apres un login reussi."""
    try:
        from app.core.redis_cache import get_redis_client

        r = get_redis_client()
        if r is not None:
            r.delete(f"login_attempts:{email}")
    except Exception as exc:
        logger.warning("clear_login_attempts_redis_error", error=str(exc))
