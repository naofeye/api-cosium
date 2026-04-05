import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.domain.schemas.documents import DocumentResponse
from app.integrations.storage import storage
from app.repositories import document_repo
from app.services import audit_service, event_service

logger = get_logger("document_service")


def list_documents(db: Session, tenant_id: int, case_id: int) -> list[DocumentResponse]:
    docs = document_repo.list_by_case(db, case_id=case_id, tenant_id=tenant_id)
    logger.info("documents_listed", tenant_id=tenant_id, case_id=case_id, count=len(docs))
    return [DocumentResponse.model_validate(d) for d in docs]


def upload_document(db: Session, tenant_id: int, case_id: int, file: UploadFile, user_id: int) -> DocumentResponse:
    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    storage_key = f"tenants/{tenant_id}/cases/{case_id}/{uuid.uuid4().hex}.{ext}"

    allowed_extensions = {"pdf", "jpg", "jpeg", "png", "docx", "xlsx", "csv", "tiff", "bmp"}
    allowed_mimes = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv",
        "image/tiff",
        "image/bmp",
    }

    if ext.lower() not in allowed_extensions:
        raise ValidationError("file", f"Type de fichier non autorise: .{ext}")
    if file.content_type and file.content_type not in allowed_mimes:
        raise ValidationError("file", f"Type MIME non autorise: {file.content_type}")

    file_data = file.file.read()
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if len(file_data) > max_size:
        raise ValidationError("file", f"Fichier trop volumineux (max {settings.max_upload_size_mb} MB)")

    storage.upload_file(
        bucket=settings.s3_bucket,
        key=storage_key,
        file_data=file_data,
        content_type=file.content_type or "application/octet-stream",
    )

    doc = document_repo.create_document(
        db,
        tenant_id=tenant_id,
        case_id=case_id,
        type="uploaded",
        filename=filename,
        storage_key=storage_key,
    )
    if user_id:
        audit_service.log_action(
            db,
            tenant_id,
            user_id,
            "create",
            "document",
            doc.id,
            new_value={"case_id": case_id, "filename": filename},
        )
    event_service.emit_event(db, tenant_id, "DocumentAjoute", "document", doc.id, user_id, {"case_id": case_id})
    logger.info("document_uploaded", tenant_id=tenant_id, case_id=case_id, document_id=doc.id, filename=filename)
    return DocumentResponse.model_validate(doc)


def get_download_url(db: Session, tenant_id: int, document_id: int, inline: bool = False) -> str:
    doc = document_repo.get_by_id(db, document_id=document_id, tenant_id=tenant_id)
    if not doc:
        raise NotFoundError("document", document_id)

    extra_params: dict[str, str] = {}
    if inline:
        extra_params["ResponseContentDisposition"] = f'inline; filename="{doc.filename}"'
    else:
        extra_params["ResponseContentDisposition"] = f'attachment; filename="{doc.filename}"'

    url = storage.get_download_url(
        bucket=settings.s3_bucket,
        key=doc.storage_key,
        expires=3600,
        extra_params=extra_params,
    )
    return url
