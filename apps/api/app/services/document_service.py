import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.domain.schemas.documents import DocumentResponse
from app.integrations.storage import storage
from app.repositories import case_repo, document_repo
from app.services import audit_service, event_service

logger = get_logger("document_service")


def list_documents(db: Session, tenant_id: int, case_id: int) -> list[DocumentResponse]:
    docs = document_repo.list_by_case(db, case_id=case_id, tenant_id=tenant_id)
    logger.info("documents_listed", tenant_id=tenant_id, case_id=case_id, count=len(docs))
    return [DocumentResponse.model_validate(d) for d in docs]


def upload_document(
    db: Session,
    tenant_id: int,
    case_id: int,
    *,
    file_data: bytes,
    filename: str,
    content_type: str | None,
    user_id: int,
) -> DocumentResponse:
    """Upload un document. Le router doit avoir appele file.read() au prealable.

    Service decouple de FastAPI/UploadFile : testable avec des bytes.
    """
    # Verrouille l'invariant tenant/case AVANT de toucher S3 ou la DB :
    # un upload avec case_id appartenant a un autre tenant doit echouer
    # 404, sinon l'integrite relationnelle se corrompt et le chemin S3
    # tenants/{X}/cases/{Y} pointe vers un dossier qui n'est pas a X.
    if case_repo.get_case(db, case_id=case_id, tenant_id=tenant_id) is None:
        raise NotFoundError("case", case_id)

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
    if content_type and content_type not in allowed_mimes:
        raise ValidationError("file", f"Type MIME non autorise: {content_type}")

    max_size = settings.max_upload_size_mb * 1024 * 1024
    if len(file_data) > max_size:
        raise ValidationError("file", f"Fichier trop volumineux (max {settings.max_upload_size_mb} MB)")

    # Verification magic bytes pour eviter les fichiers deguises
    _magic = {
        b"%PDF": "pdf",
        b"\xff\xd8\xff": "jpg",
        b"\x89PNG": "png",
        b"PK\x03\x04": "docx",  # ZIP-based (docx, xlsx)
        b"II\x2a\x00": "tiff",
        b"MM\x00\x2a": "tiff",
        b"BM": "bmp",
    }
    detected_ext = None
    for magic, magic_ext in _magic.items():
        if file_data[:len(magic)] == magic:
            detected_ext = magic_ext
            break
    # CSV/text n'ont pas de magic bytes — on les accepte si ext=csv
    if detected_ext and ext.lower() not in ("csv",) and detected_ext != ext.lower():
        # docx et xlsx partagent le meme magic (PK/ZIP)
        if not (detected_ext == "docx" and ext.lower() in ("docx", "xlsx")):
            raise ValidationError("file", f"Le contenu du fichier ne correspond pas a l'extension .{ext}")

    storage.upload_file(
        bucket=settings.s3_bucket,
        key=storage_key,
        file_data=file_data,
        content_type=content_type or "application/octet-stream",
    )

    # Cleanup S3 si la transaction DB echoue (creation, audit, event ou commit final).
    # Sans ce nettoyage, un objet S3 orphelin reste meme si la ligne Document est rollbackee.
    try:
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

        # Commit explicite : on veut etre sur que la ligne Document est durablement
        # persistee AVANT de declarer l'upload reussi. Si le commit echoue, on
        # supprime l'objet S3 pour eviter un orphelin.
        db.commit()
    except Exception:
        try:
            db.rollback()
        except SQLAlchemyError:
            pass
        try:
            storage.delete_file(bucket=settings.s3_bucket, key=storage_key)
        except (ConnectionError, TimeoutError, OSError) as cleanup_err:
            logger.warning("orphan_file_cleanup_failed", key=storage_key, error=str(cleanup_err))
        raise

    logger.info("document_uploaded", tenant_id=tenant_id, case_id=case_id, document_id=doc.id, filename=filename)
    return DocumentResponse.model_validate(doc)


def _sanitize_filename(name: str) -> str:
    """Remove characters that could cause header injection."""
    return name.replace('"', "").replace("\\", "_").replace("\n", "").replace("\r", "")


def get_download_url(db: Session, tenant_id: int, document_id: int, inline: bool = False) -> str:
    doc = document_repo.get_by_id(db, document_id=document_id, tenant_id=tenant_id)
    if not doc:
        raise NotFoundError("document", document_id)

    safe_filename = _sanitize_filename(doc.filename)
    extra_params: dict[str, str] = {}
    if inline:
        extra_params["ResponseContentDisposition"] = f'inline; filename="{safe_filename}"'
    else:
        extra_params["ResponseContentDisposition"] = f'attachment; filename="{safe_filename}"'

    url = storage.get_download_url(
        bucket=settings.s3_bucket,
        key=doc.storage_key,
        expires=3600,
        extra_params=extra_params,
    )
    return url
