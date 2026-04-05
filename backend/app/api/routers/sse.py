import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.models.notification import Notification

router = APIRouter(prefix="/api/v1/sse", tags=["sse"])

POLL_INTERVAL_SECONDS = 5
MAX_EVENTS_PER_POLL = 10


async def event_generator(
    db: Session,
    user_id: int,
    tenant_id: int,
    request: Request,
) -> None:
    """Generate SSE events by polling the notifications table."""
    # Determine starting point: skip existing notifications
    last_id: int = (
        db.scalar(
            select(func.max(Notification.id)).where(
                Notification.tenant_id == tenant_id,
                Notification.user_id == user_id,
            )
        )
        or 0
    )

    while True:
        if await request.is_disconnected():
            break

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

        # Expire cached ORM objects so next poll sees fresh DB state
        db.expire_all()
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@router.get(
    "/notifications",
    summary="Flux SSE de notifications",
    description="Flux temps reel des nouvelles notifications via Server-Sent Events.",
)
async def stream_notifications(
    request: Request,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> StreamingResponse:
    """SSE stream of new notifications for the authenticated user."""
    return StreamingResponse(
        event_generator(db, tenant_ctx.user_id, tenant_ctx.tenant_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
