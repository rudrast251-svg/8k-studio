import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

_PATTERN = re.compile(r'\b8K\b', re.IGNORECASE)


@register.filter
def highlight_8k(value):
    """Wraps standalone "8K" occurrences in a gradient span for the hero headline."""
    escaped = escape(value or '')
    highlighted = _PATTERN.sub(lambda m: f'<span class="grad">{m.group(0)}</span>', escaped)
    return mark_safe(highlighted)
