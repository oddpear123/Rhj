import os
import uuid
import io
from pathlib import Path
from PIL import Image, ImageFilter

# ── Storage mode detection ──────────────────────────────────────────────────
OCI_NAMESPACE = os.getenv("OCI_NAMESPACE", "")
OCI_BUCKET = os.getenv("OCI_BUCKET", "")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")

USE_OCI = bool(OCI_NAMESPACE and OCI_BUCKET)
USE_S3 = bool(AWS_ACCESS_KEY_ID) and not USE_OCI
USE_LOCAL = not USE_OCI and not USE_S3

# Local storage paths
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
API_BASE = os.getenv("API_BASE_URL", "http://129.159.34.144:8000")

if USE_LOCAL:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / "photos").mkdir(exist_ok=True)
    (UPLOAD_DIR / "previews").mkdir(exist_ok=True)
elif USE_S3:
    import boto3

    S3_BUCKET = os.getenv("S3_BUCKET", "redhot-photos")
    S3_REGION = os.getenv("S3_REGION", "us-east-1")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    PRESIGNED_URL_EXPIRY = int(os.getenv("PRESIGNED_URL_EXPIRY", "3600"))

    s3 = boto3.client(
        "s3",
        region_name=S3_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
elif USE_OCI:
    import oci

    OCI_REGION = os.getenv("OCI_REGION", "us-sanjose-1")
    OCI_CONFIG_FILE = os.getenv("OCI_CONFIG_FILE", "~/.oci/config")
    OCI_CONFIG_PROFILE = os.getenv("OCI_CONFIG_PROFILE", "DEFAULT")

    try:
        oci_config = oci.config.from_file(OCI_CONFIG_FILE, OCI_CONFIG_PROFILE)
        oci_config["region"] = OCI_REGION
        object_storage = oci.object_storage.ObjectStorageClient(oci_config)
    except Exception:
        # Fallback to instance principal (when running on OCI compute)
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        object_storage = oci.object_storage.ObjectStorageClient({}, signer=signer)


def upload_photo(file_bytes: bytes, original_filename: str) -> tuple[str, str]:
    """Upload full + blurred preview. Returns (key, preview_key)."""
    ext = os.path.splitext(original_filename)[1].lower() or ".jpg"
    unique_id = uuid.uuid4().hex
    photo_key = f"photos/{unique_id}{ext}"
    preview_key = f"previews/{unique_id}{ext}"

    # Generate blurred preview
    img = Image.open(io.BytesIO(file_bytes))
    img.thumbnail((800, 800))
    blurred = img.filter(ImageFilter.GaussianBlur(radius=20))
    buf = io.BytesIO()
    save_format = img.format or "JPEG"
    blurred.save(buf, format=save_format, quality=60)
    buf.seek(0)
    preview_bytes = buf.getvalue()

    if USE_LOCAL:
        (UPLOAD_DIR / photo_key).write_bytes(file_bytes)
        (UPLOAD_DIR / preview_key).write_bytes(preview_bytes)
    elif USE_S3:
        s3.put_object(Bucket=S3_BUCKET, Key=photo_key, Body=file_bytes, ContentType=_content_type(ext))
        s3.put_object(Bucket=S3_BUCKET, Key=preview_key, Body=preview_bytes, ContentType=_content_type(ext))
    elif USE_OCI:
        object_storage.put_object(
            namespace_name=OCI_NAMESPACE,
            bucket_name=OCI_BUCKET,
            object_name=photo_key,
            put_object_body=file_bytes,
            content_type=_content_type(ext),
        )
        object_storage.put_object(
            namespace_name=OCI_NAMESPACE,
            bucket_name=OCI_BUCKET,
            object_name=preview_key,
            put_object_body=preview_bytes,
            content_type=_content_type(ext),
        )

    return photo_key, preview_key


def get_presigned_url(key: str) -> str:
    """Return a URL for the given storage key."""
    if USE_LOCAL:
        return f"{API_BASE}/uploads/{key}"
    elif USE_S3:
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=PRESIGNED_URL_EXPIRY,
        )
    elif USE_OCI:
        # Serve through backend media proxy
        return f"{API_BASE}/media/{key}"
    return ""


def get_object_bytes(key: str) -> bytes | None:
    """Fetch raw bytes from storage. Used by the media proxy endpoint."""
    if USE_LOCAL:
        path = UPLOAD_DIR / key
        if path.exists():
            return path.read_bytes()
        return None
    elif USE_S3:
        try:
            resp = s3.get_object(Bucket=S3_BUCKET, Key=key)
            return resp["Body"].read()
        except Exception:
            return None
    elif USE_OCI:
        try:
            resp = object_storage.get_object(
                namespace_name=OCI_NAMESPACE,
                bucket_name=OCI_BUCKET,
                object_name=key,
            )
            return resp.data.content
        except Exception:
            return None
    return None


def delete_photo(photo_key: str, preview_key: str):
    if USE_LOCAL:
        for k in (photo_key, preview_key):
            p = UPLOAD_DIR / k
            if p.exists():
                p.unlink()
    elif USE_S3:
        s3.delete_object(Bucket=S3_BUCKET, Key=photo_key)
        s3.delete_object(Bucket=S3_BUCKET, Key=preview_key)
    elif USE_OCI:
        for key in (photo_key, preview_key):
            try:
                object_storage.delete_object(
                    namespace_name=OCI_NAMESPACE,
                    bucket_name=OCI_BUCKET,
                    object_name=key,
                )
            except Exception:
                pass


def _content_type(ext: str) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(ext, "application/octet-stream")
