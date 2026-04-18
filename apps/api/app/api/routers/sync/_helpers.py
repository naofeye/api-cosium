"""Helpers partagés par les sous-routers sync (locks + cache invalidation)."""

from app.core.exceptions import BusinessError
from app.core.redis_cache import acquire_lock, cache_delete_pattern


def invalidate_tenant_caches(tenant_id: int) -> None:
    """Invalidate all cached data for a tenant after sync operations."""
    cache_delete_pattern(f"analytics:*:{tenant_id}*")
    cache_delete_pattern(f"admin:metrics:{tenant_id}")
    cache_delete_pattern(f"admin:data_quality:{tenant_id}")
    cache_delete_pattern(f"client:quick:{tenant_id}:*")
    cache_delete_pattern(f"dashboard:*:{tenant_id}*")


def acquire_sync_lock(lock_key: str, message: str, ttl: int = 1200) -> None:
    """Raise BusinessError SYNC_IN_PROGRESS si le lock est déjà pris."""
    if not acquire_lock(lock_key, ttl=ttl):
        raise BusinessError(message=message, code="SYNC_IN_PROGRESS")
