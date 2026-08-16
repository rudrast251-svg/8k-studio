from .models import SiteConfig


def _hex_to_rgb_string(value, fallback):
    value = (value or '').lstrip('#')
    if len(value) != 6:
        return fallback
    try:
        r, g, b = (int(value[i:i + 2], 16) for i in (0, 2, 4))
        return f'{r}, {g}, {b}'
    except ValueError:
        return fallback


def site_config(request):
    try:
        config = SiteConfig.load()
    except Exception:
        return {'site_config': None, 'theme_vars': None}

    theme_vars = {
        'violet': config.primary_color,
        'blue': config.accent_color,
        'bg': config.background_color,
        'violet_rgb': _hex_to_rgb_string(config.primary_color, '139, 92, 246'),
        'blue_rgb': _hex_to_rgb_string(config.accent_color, '59, 130, 246'),
    }
    return {'site_config': config, 'theme_vars': theme_vars}
