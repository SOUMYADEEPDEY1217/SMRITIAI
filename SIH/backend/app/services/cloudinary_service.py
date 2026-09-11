"""
Photo storage via Cloudinary instead of Firebase Storage - Firebase Storage
now requires the paid Blaze plan even for free-tier usage, Cloudinary's free
tier (25GB, no card required) covers this fine for a hackathon prototype.

Firestore + Firebase Auth are unaffected - only WHERE photos physically live
changed. Everything else (routes, memory records) still just stores/reads a
photo_url string, so this swap doesn't ripple anywhere else in the app.

SECURITY: dest_path is always built server-side from user['uid'] (from a
verified token) and a server-generated memory_id (uuid4) - never from raw
client input - so there's no path-traversal or overwrite-another-user's-photo
risk here.
"""
import logging
from app.config import settings

logger = logging.getLogger("cloudinary_service")

try:
    import cloudinary
    import cloudinary.uploader
    _CLOUDINARY_AVAILABLE = True
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )
except Exception as e:
    cloudinary = None
    _CLOUDINARY_AVAILABLE = False
    logger.warning(f"cloudinary unavailable ({e}). Photo upload endpoint will be disabled.")


def upload_photo(image_bytes: bytes, dest_path: str, resource_type: str = "auto") -> str:
    """
    dest_path example: users/{user_id}/memories/{memory_id}
    Returns a public HTTPS URL to the uploaded asset.
    """
    if not _CLOUDINARY_AVAILABLE:
        raise RuntimeError("Photo storage is not available on this server (cloudinary not installed/configured).")

    result = cloudinary.uploader.upload(
        image_bytes,
        public_id=dest_path,
        folder=None,
        resource_type=resource_type,
        overwrite=True,
    )
    return result["secure_url"]


def delete_photo(dest_path: str, resource_type: str = "image") -> None:
    """Deletes a previously-uploaded asset by its public_id."""
    if not _CLOUDINARY_AVAILABLE:
        return
    try:
        cloudinary.uploader.destroy(dest_path, resource_type=resource_type)
    except Exception as e:
        logger.warning(f"Failed to delete Cloudinary asset '{dest_path}': {e}")
