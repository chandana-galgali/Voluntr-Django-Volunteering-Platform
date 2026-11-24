import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from core.models import Opportunity, Article


def legacy_slug(title):
    return slugify(title.encode('utf-8').decode('cp1252', errors='replace'))


def asset(group, slug):
    base = Path(__file__).resolve().parents[3] / 'static' / 'img'
    for ext in ('.jpg', '.svg'):
        if (base / group / (slug+ext)).is_file():
            return 'img/'+group+'/'+slug+ext
    return 'img/hero.jpg'


class Command(BaseCommand):
    help = 'Load or refresh labeled sample opportunities and journal articles.'

    @transaction.atomic
    def handle(self, *args, **options):
        data = json.loads((Path(__file__).resolve().parents[2] / 'demo_content.json').read_text(encoding='utf-8'))
        for title, cat, city, mode, skills, summary, description in data['opportunities']:
            slug = slugify(title)
            values = dict(title=title, category=cat, city=city, mode=mode, skills=skills, summary=summary, description=description+'\n\nBefore attending, confirm training, accessibility, schedule and safety requirements with the organizer. This is a demonstration role, not a real confirmed event.', organization='Voluntr Demo Collective', commitment='2–4 hours/week', image=asset('opportunities', slug))
            row = Opportunity.objects.filter(demo=True, slug=slug).first() or Opportunity.objects.filter(demo=True, slug=legacy_slug(title)).first()
            if row:
                for key, value in values.items(): setattr(row, key, value)
                # Keep the existing slug and primary key to preserve links and applications.
                row.save(update_fields=list(values))
            elif not Opportunity.objects.filter(slug=slug).exists():
                Opportunity.objects.create(slug=slug, **values, slots=12, published=True, demo=True)
        for title, cat, summary, body in data['articles']:
            slug = slugify(title)
            values = dict(title=title, category=cat, summary=summary, body=body, image=asset('journal', slug))
            row = Article.objects.filter(slug=slug).first() or Article.objects.filter(slug=legacy_slug(title)).first()
            if row:
                for key, value in values.items(): setattr(row, key, value)
                row.save(update_fields=list(values))
            else:
                Article.objects.create(slug=slug, **values)
        self.stdout.write(self.style.SUCCESS('Demo content refreshed.'))
