from pathlib import Path
import json
from django import template
from django.conf import settings
register = template.Library()

@register.filter
def photo_path(value):
    if not isinstance(value, str) or not value.startswith('img/') or '..' in Path(value).parts:
        return 'img/hero.jpg'
    base = Path(settings.BASE_DIR) / 'static'
    p = Path(value)
    for candidate in (str(p.with_suffix('.jpg')).replace('\\','/'), value, str(p.with_suffix('.svg')).replace('\\','/')):
        if (base / candidate).is_file():
            return candidate
    return 'img/hero.jpg'

@register.filter
def photo_width(value):
    try:
        manifest = Path(settings.BASE_DIR) / 'static' / 'img' / 'photo-dimensions.json'
        return json.loads(manifest.read_text(encoding='utf-8')).get(photo_path(value), 1600)
    except (OSError, ValueError):
        return 1600
