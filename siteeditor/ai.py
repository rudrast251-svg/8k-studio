"""Parses a plain-English website-editing command into a patch dict that can
be applied directly to a SiteConfig instance.
"""
import json
import re

import requests
from django.conf import settings

PATCHABLE_FIELDS = {
    'headline', 'subheadline', 'primary_color', 'accent_color', 'background_color',
    'hero_autoplay', 'hero_muted', 'hero_loop', 'cta_label',
}

COLOR_WORDS = {
    'black': '#05050a', 'white': '#f5f5f7', 'gold': '#d4af37', 'golden': '#d4af37',
    'purple': '#8b5cf6', 'violet': '#8b5cf6', 'blue': '#3b82f6', 'navy': '#0f1b3d',
    'red': '#ef4444', 'crimson': '#dc2626', 'green': '#22c55e', 'emerald': '#10b981',
    'teal': '#14b8a6', 'pink': '#ec4899', 'orange': '#f97316', 'amber': '#f59e0b',
    'silver': '#c0c0c0', 'grey': '#6b7280', 'gray': '#6b7280',
}

COLOR_THEMES = {
    ('black', 'gold'): {'background_color': '#05050a', 'primary_color': '#d4af37', 'accent_color': '#f2c94c'},
    ('black', 'purple'): {'background_color': '#05050a', 'primary_color': '#8b5cf6', 'accent_color': '#3b82f6'},
    ('black', 'violet'): {'background_color': '#05050a', 'primary_color': '#8b5cf6', 'accent_color': '#3b82f6'},
    ('black', 'blue'): {'background_color': '#05050a', 'primary_color': '#3b82f6', 'accent_color': '#06b6d4'},
    ('black', 'red'): {'background_color': '#05050a', 'primary_color': '#ef4444', 'accent_color': '#f97316'},
    ('black', 'green'): {'background_color': '#05050a', 'primary_color': '#22c55e', 'accent_color': '#14b8a6'},
}


def _extract_quoted(text: str) -> str | None:
    match = re.search(r'["“‘]([^"”’]{2,140})["”’]', text)
    return match.group(1) if match else None


def _keyword_parse(text: str) -> dict:
    t = text.lower()
    patch = {}

    hex_codes = re.findall(r'#[0-9a-fA-F]{6}\b', text)
    color_names = [w for w in COLOR_WORDS if re.search(rf'\b{w}\b', t)]

    theme_hit = None
    for combo, colors in COLOR_THEMES.items():
        if all(word in color_names for word in combo):
            theme_hit = colors
            break
    if theme_hit and ('color' in t or 'colour' in t or 'theme' in t):
        patch.update(theme_hit)
    elif hex_codes and ('color' in t or 'colour' in t):
        patch['primary_color'] = hex_codes[0]
        if len(hex_codes) > 1:
            patch['accent_color'] = hex_codes[1]
    elif color_names and ('color' in t or 'colour' in t or 'theme' in t):
        if 'background' in t or 'bg' in t:
            patch['background_color'] = COLOR_WORDS[color_names[0]]
        else:
            patch['primary_color'] = COLOR_WORDS[color_names[0]]
            if len(color_names) > 1:
                patch['accent_color'] = COLOR_WORDS[color_names[1]]

    if any(w in t for w in ['headline', 'title', 'heading']):
        quoted = _extract_quoted(text)
        if quoted:
            patch['headline'] = quoted
    if any(w in t for w in ['subheadline', 'subtitle', 'description', 'tagline']):
        quoted = _extract_quoted(text)
        if quoted:
            patch['subheadline'] = quoted
    if any(w in t for w in ['button text', 'button label', 'cta text', 'cta label']):
        quoted = _extract_quoted(text)
        if quoted:
            patch['cta_label'] = quoted

    if 'autoplay' in t:
        patch['hero_autoplay'] = 'no' not in t.split('autoplay')[0][-12:] and 'stop' not in t and "don't" not in t
    if any(w in t for w in ['silent', 'mute', 'muted', 'no sound', 'no audio']):
        patch['hero_muted'] = True
    if any(w in t for w in ['unmute', 'with sound', 'with audio', 'turn on sound']):
        patch['hero_muted'] = False
    if 'loop' in t:
        patch['hero_loop'] = 'stop' not in t and "don't" not in t

    return patch


def _anthropic_parse(text: str) -> dict | None:
    if not settings.ANTHROPIC_API_KEY:
        return None
    system = (
        "You convert a plain-English website-editing instruction into strict JSON for a landing "
        f"page config. Return ONLY a JSON object using a subset of these keys: {sorted(PATCHABLE_FIELDS)}. "
        "Colors must be hex strings like \"#111111\". Booleans for hero_autoplay/hero_muted/hero_loop. "
        "Only include keys the instruction actually changes. No other text."
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
        return {k: v for k, v in parsed.items() if k in PATCHABLE_FIELDS}
    except (requests.RequestException, KeyError, json.JSONDecodeError, IndexError):
        return None


def parse_site_command(text: str) -> dict:
    keyword_patch = _keyword_parse(text)
    ai_patch = _anthropic_parse(text)
    if ai_patch:
        merged = dict(keyword_patch)
        merged.update(ai_patch)
        return merged
    return keyword_patch


def wants_hero_video(text: str) -> bool:
    t = text.lower()
    return 'hero' in t and ('video' in t or 'banner' in t)


def wants_hero_image(text: str) -> bool:
    t = text.lower()
    return 'hero' in t and 'image' in t and 'video' not in t
