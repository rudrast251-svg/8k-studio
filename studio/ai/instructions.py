"""Turns a user's free-text instruction into a structured set of enhancement
operations. Uses the Anthropic API for flexible natural-language understanding
when ANTHROPIC_API_KEY is configured, and always falls back to a deterministic
keyword parser so the feature works with zero API keys configured (demo mode).
"""
import json
import re

import requests
from django.conf import settings

IMAGE_OP_KEYS = [
    'upscale', 'target_resolution', 'sharpen', 'denoise', 'brighten', 'darken',
    'color_boost', 'face_restore', 'remove_background', 'cinematic',
]
VIDEO_OP_KEYS = [
    'upscale', 'target_resolution', 'sharpen', 'denoise', 'brighten', 'darken',
    'color_boost', 'stabilize', 'interpolate_frames', 'mute_audio', 'cinematic',
]

DEFAULT_OPS = {
    'upscale': False,
    'target_resolution': '4K',
    'sharpen': False,
    'denoise': False,
    'brighten': False,
    'darken': False,
    'color_boost': False,
    'face_restore': False,
    'remove_background': False,
    'stabilize': False,
    'interpolate_frames': False,
    'mute_audio': False,
    'cinematic': False,
}


def _keyword_parse(text: str) -> dict:
    t = text.lower()
    ops = dict(DEFAULT_OPS)

    if '8k' in t:
        ops['upscale'] = True
        ops['target_resolution'] = '8K'
    elif '4k' in t:
        ops['upscale'] = True
        ops['target_resolution'] = '4K'
    if any(w in t for w in ['upscale', 'enhance', 'higher resolution', 'increase resolution', 'hd', 'high quality']):
        ops['upscale'] = True

    if any(w in t for w in ['blur', 'sharp', 'clarity', 'crisp', 'detail']):
        ops['sharpen'] = True
    if any(w in t for w in ['noise', 'grain', 'denoise', 'clean up']):
        ops['denoise'] = True
    if any(w in t for w in ['bright', 'lighting', 'expose', 'light up', 'dark video', 'dark photo']):
        ops['brighten'] = True
    if any(w in t for w in ['darker', 'dim', 'reduce brightness']):
        ops['darken'] = True
    if any(w in t for w in ['color', 'colour', 'vibrant', 'vivid', 'saturation', 'pop']):
        ops['color_boost'] = True
    if any(w in t for w in ['face', 'restore face', 'faces']):
        ops['face_restore'] = True
    if 'background' in t and any(w in t for w in ['remove', 'no ', 'without', 'delete', 'transparent', 'cut out', 'erase']):
        ops['remove_background'] = True
    if any(w in t for w in ['cinematic', 'movie', 'film look', 'film-like', 'professional look']):
        ops['cinematic'] = True

    if any(w in t for w in ['stabilize', 'stabilise', 'shaky', 'shake', 'steady']):
        ops['stabilize'] = True
    if any(w in t for w in ['smooth', 'smoother', 'interpolate', 'slow motion', 'slow-mo', 'fps', 'frame rate', '60fps', '60 fps']):
        ops['interpolate_frames'] = True
    if any(w in t for w in ['mute', 'silent', 'no audio', 'remove audio', 'without sound']):
        ops['mute_audio'] = True

    return ops


def _anthropic_parse(text: str, media_kind: str) -> dict | None:
    if not settings.ANTHROPIC_API_KEY:
        return None
    allowed_keys = IMAGE_OP_KEYS if media_kind == 'image' else VIDEO_OP_KEYS
    system = (
        "You convert a user's plain-English media-enhancement request into strict JSON. "
        f"Return ONLY a JSON object with boolean fields chosen from {allowed_keys}, plus "
        "\"target_resolution\" as \"4K\" or \"8K\". Do not include any other text, keys, or markdown."
    )
    try:
        resp = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': settings.ANTHROPIC_API_KEY,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            json={
                'model': settings.ANTHROPIC_MODEL,
                'max_tokens': 300,
                'system': system,
                'messages': [{'role': 'user', 'content': text}],
            },
            timeout=15,
        )
        resp.raise_for_status()
        content = resp.json()['content'][0]['text']
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if not match:
            return None
        parsed = json.loads(match.group(0))
        ops = dict(DEFAULT_OPS)
        for key in allowed_keys:
            if key in parsed:
                ops[key] = parsed[key]
        return ops
    except (requests.RequestException, KeyError, json.JSONDecodeError, IndexError):
        return None


def parse_instruction(text: str, media_kind: str) -> dict:
    """Return a dict of enhancement operations for the given instruction."""
    ai_ops = _anthropic_parse(text, media_kind)
    keyword_ops = _keyword_parse(text)
    if ai_ops is None:
        return keyword_ops
    # Merge: trust the AI parse, but OR in obvious keyword matches it may have missed.
    merged = dict(ai_ops)
    for key, value in keyword_ops.items():
        if isinstance(value, bool) and value:
            merged[key] = True
    return merged


def humanize_ops(ops: dict) -> list[str]:
    labels = {
        'upscale': f"Upscale to {ops.get('target_resolution', '4K')}",
        'sharpen': 'Sharpen details',
        'denoise': 'Reduce noise',
        'brighten': 'Brighten',
        'darken': 'Darken',
        'color_boost': 'Improve colors',
        'face_restore': 'Restore faces',
        'remove_background': 'Remove background',
        'cinematic': 'Cinematic color grade',
        'stabilize': 'Stabilize',
        'interpolate_frames': 'Smooth motion (frame interpolation)',
        'mute_audio': 'Mute audio',
    }
    return [label for key, label in labels.items() if ops.get(key)]
