"""Image enhancement pipeline.

Two execution paths:
  * Real GPU path — used automatically when REPLICATE_API_TOKEN is set. Calls
    a real Real-ESRGAN model on Replicate for true AI super-resolution.
  * Demo path — used when no provider key is configured. Performs genuine,
    if more modest, local image processing with Pillow/OpenCV so every
    feature is actually clickable and produces a real transformed file,
    while being transparent in the UI that it is not full neural 8K upscaling.
"""
import io

import cv2
import numpy as np
from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageEnhance, ImageFilter

from . import replicate_client

DEMO_MAX_EDGE = {'4K': 3840, '8K': 4096}
UPSCALE_FACTOR = {'4K': 2, '8K': 4}


def enhance_image_demo(asset, ops: dict) -> tuple[bytes, str, list[str], list[str]]:
    """Run local Pillow/OpenCV processing. Returns (bytes, content_type, applied, skipped)."""
    applied, skipped = [], []
    asset.file.open('rb')
    try:
        pil_img = Image.open(asset.file).convert('RGB')
    finally:
        asset.file.close()

    if ops.get('upscale'):
        target = ops.get('target_resolution', '4K')
        factor = UPSCALE_FACTOR.get(target, 2)
        new_size = (pil_img.width * factor, pil_img.height * factor)
        max_edge = DEMO_MAX_EDGE.get(target, 3840)
        if max(new_size) > max_edge:
            scale = max_edge / max(new_size)
            new_size = (int(new_size[0] * scale), int(new_size[1] * scale))
        pil_img = pil_img.resize(new_size, Image.LANCZOS)
        applied.append(f'Upscaled {factor}x (demo bicubic/Lanczos resample, capped at {max_edge}px)')

    if ops.get('denoise'):
        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        cv_img = cv2.fastNlMeansDenoisingColored(cv_img, None, 6, 6, 7, 21)
        pil_img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
        applied.append('Reduced noise (OpenCV fastNlMeans denoising)')

    if ops.get('sharpen'):
        pil_img = pil_img.filter(ImageFilter.UnsharpMask(radius=2.2, percent=140, threshold=2))
        applied.append('Sharpened details (unsharp mask)')

    if ops.get('brighten'):
        pil_img = ImageEnhance.Brightness(pil_img).enhance(1.18)
        applied.append('Brightened')

    if ops.get('darken'):
        pil_img = ImageEnhance.Brightness(pil_img).enhance(0.85)
        applied.append('Darkened')

    if ops.get('color_boost'):
        pil_img = ImageEnhance.Color(pil_img).enhance(1.25)
        applied.append('Boosted color vibrance')

    if ops.get('cinematic'):
        pil_img = ImageEnhance.Contrast(pil_img).enhance(1.12)
        pil_img = ImageEnhance.Color(pil_img).enhance(1.1)
        pil_img = ImageEnhance.Brightness(pil_img).enhance(0.97)
        applied.append('Applied cinematic color grade')

    if ops.get('face_restore'):
        skipped.append('Face restoration (needs a connected AI provider such as GFPGAN via Replicate)')

    if ops.get('remove_background'):
        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        mask = np.zeros(cv_img.shape[:2], np.uint8)
        bgd_model, fgd_model = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
        h, w = cv_img.shape[:2]
        rect = (int(w * 0.03), int(h * 0.03), int(w * 0.94), int(h * 0.94))
        try:
            cv2.grabCut(cv_img, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
            mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
            rgba = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGBA)
            rgba[:, :, 3] = mask2 * 255
            pil_img = Image.fromarray(cv2.cvtColor(rgba, cv2.COLOR_BGRA2RGBA))
            applied.append('Removed background (GrabCut segmentation)')
        except cv2.error:
            skipped.append('Background removal (image too small/uniform for automatic segmentation)')

    buffer = io.BytesIO()
    fmt = 'PNG' if pil_img.mode == 'RGBA' else 'JPEG'
    pil_img.save(buffer, format=fmt, quality=95)
    content_type = 'image/png' if fmt == 'PNG' else 'image/jpeg'
    return buffer.getvalue(), content_type, applied, skipped


def enhance_image_replicate(asset, ops: dict) -> tuple[bytes, str, list[str], list[str]]:
    """Run enhancement via the real Replicate GPU API."""
    applied, skipped = [], []
    image_url = f"{settings.SITE_BASE_URL}{asset.file.url}"
    payload = {
        'image': image_url,
        'scale': UPSCALE_FACTOR.get(ops.get('target_resolution', '4K'), 2) if ops.get('upscale') else 1,
        'face_enhance': bool(ops.get('face_restore')),
    }
    prediction = replicate_client.create_prediction(settings.REPLICATE_IMAGE_MODEL, payload)
    prediction = replicate_client.wait_for_prediction(prediction['id'])
    if prediction['status'] != 'succeeded':
        raise RuntimeError(f"Replicate prediction failed: {prediction.get('error', 'unknown error')}")
    output_url = prediction['output']
    if isinstance(output_url, list):
        output_url = output_url[0]

    import requests
    resp = requests.get(output_url, timeout=120)
    resp.raise_for_status()
    applied.append(f"AI upscaled via Replicate ({settings.REPLICATE_IMAGE_MODEL.split(':')[0]})")
    if ops.get('face_restore'):
        applied.append('Restored faces (GFPGAN via provider)')
    content_type = resp.headers.get('content-type', 'image/png')
    return resp.content, content_type, applied, skipped


def run(asset, ops: dict):
    if settings.REPLICATE_API_TOKEN:
        return enhance_image_replicate(asset, ops), 'replicate'
    return enhance_image_demo(asset, ops), 'demo'
