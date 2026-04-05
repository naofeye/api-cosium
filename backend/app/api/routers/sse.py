import asyncio
import json
import time
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import SessionLocal
from app.models.notification import Notification

router = APIRouter(prefix="/api/v1/sse", tags=["sse"])

POLL_INTERVAL_SECONDS = 5
MAX_EVENTS_PER_POLL = 10
MAX_CONNECTION_SECONDS = 300  # 5 min max; client should auto-reconnect
HEARTBEAT_INTERVAL = 30  # Keep-alive comment every 30s


async def event_generator(
    user_id: int,
    tenant_id: int,
    request: Request,
) -> AsyncGenerator[str, None]:
    """Generate SSE events by polling the notifications table.

    Uses a short-lived DB session per poll iteration to avoid holding a
    connection pool slot open for the entire SSE stream lifetime.
    Limits total connection time to MAX_CONNECTION_SECONDS so the client
    reconnects periodically, preventing resource accumulation.
    """
    start_time = time.monotonic()
    last_heartbeat = start_time

    # Determine starting point: skip existing notifications
    db = SessionLocal()
    try:
        last_id: int = (
            db.scalar(
                select(func.max(Notification.id)).where(
                    Notification.tenant_id == tenant_id,
                    Notification.user_id == user_id,
                )
            )
            or 0
        )
    finally:
        db.close()

    while True:
        if await request.is_disconnected():
            break

        # Close connection after max lifetime; client auto-reconnects via EventSource
        if time.monotonic() - start_time > MAX_CONNECTION_SECONDS:
            yield "event: reconnect\ndata: {}\n\n"
            break

        db = SessionLocal()
        try:
            new_notifs = db.scalars(
                select(Notification)
                .where(
                    Notification.tenant_id == tenant_id,
                    Notification.user_id == user_id,
                    Notification.id > last_id,
                )
                .order_by(Notification.id.asc())
                .limit(MAX_EVENTS_PER_POLL)
            ).all()

            for notif in new_notifs:
                data = json.dumps(
                    {
                        "id": notif.id,
                        "type": notif.type,
                        "title": notif.title,
                        "message": notif.message,
                        "entity_type": notif.entity_type,
                        "entity_id": notif.entity_id,
                        "created_at": str(notif.created_at),
                    },
                    ensure_ascii=False,
                )
                yield f"data: {data}\n\n"
                last_id = notif.id
        finally:
            db.close()

        # Periodic heartbeat so proxies and browsers detect stale connections
        now = time.monotonic()
        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
            yield ": heartbeat\n\n"
            last_heartbeat = now

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@router.get(
    "/notifications",
    summary="Flux SSE de notifications",
    description="Flux temps reel des nouvelles notifications via Server-Sent Events.",
)
async def stream_notifications(
    request: Request,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> StreamingResponse:
    """SSE stream of new notifications for the authenticated user."""
    return StreamingResponse(
        event_generator(tenant_ctx.user_id, tenant_ctx.tenant_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
