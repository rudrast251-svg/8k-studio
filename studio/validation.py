import os

from django.conf import settings
from django.core.exceptions import ValidationError


class UploadValidationError(ValidationError):
    pass


def detect_kind(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext in settings.ALLOWED_IMAGE_EXTENSIONS:
        return 'image'
    if ext in settings.ALLOWED_VIDEO_EXTENSIONS:
        return 'video'
    raise UploadValidationError(
        f'Unsupported file type "{ext}". Allowed: '
        f'{", ".join(settings.ALLOWED_IMAGE_EXTENSIONS + settings.ALLOWED_VIDEO_EXTENSIONS)}.'
    )


def validate_upload(uploaded_file) -> str:
    """Validate an uploaded file, returning its media kind ('image'/'video')."""
    kind = detect_kind(uploaded_file.name)
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if uploaded_file.size > max_bytes:
        raise UploadValidationError(
            f'File is too large ({uploaded_file.size / (1024 * 1024):.1f} MB). '
            f'Maximum allowed is {settings.MAX_UPLOAD_SIZE_MB} MB.'
        )
    if uploaded_file.size == 0:
        raise UploadValidationError('The uploaded file is empty.')
    return kind
