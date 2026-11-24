import json
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from core.models import Opportunity, Article

DEMO_ORGANIZATION = 'Voluntr Demo Collective'
SAMPLE_NOTE = '\n\nThis is a sample organization profile created for demonstration purposes. It does not represent a real registered organization.'
# (name, city, website, causes served, bio)
DEMO_ORGANIZATIONS = [
    ('Bright Futures Learning Trust (Sample)', 'Mumbai', ['Education'], 'Supports after-school learning circles, reading clubs and homework help for children in under-resourced neighbourhoods.'),
    ('Green Streets Collective (Sample)', 'Mumbai', ['Environment'], 'Organizes neighbourhood clean-ups, community gardens and waste-sorting drives with local residents.'),
    ('Paws & Care Shelter Network (Sample)', 'Thane', ['Animals'], 'Runs shelter support shifts, adoption days and enrichment activities for rescued animals.'),
    ('Shared Plate Food Bank (Sample)', 'Mumbai', ['Food security'], 'Collects, sorts and distributes food kits and prepares community meals for families in need.'),
    ('Silver Circle Community Care (Sample)', 'Pune', ['Community'], 'Brings companionship, outreach and practical support to older adults and people experiencing homelessness.'),
    ('Wellbeing First Health Alliance (Sample)', 'Delhi', ['Health'], 'Runs public-health awareness campaigns and peer-support programmes focused on mental and physical wellbeing.'),
    ('ReadyHands Relief Network (Sample)', 'Chennai', ['Disaster relief'], 'Trains volunteers to support relief logistics, supply distribution and community preparedness.'),
    ('Open Code for Good (Sample)', 'Bengaluru', ['Technology'], 'Connects tech volunteers with non-profits for accessibility reviews, digital literacy and website support.'),
    ('Play Forward Youth Sports (Sample)', 'Bengaluru', ['Sports'], 'Uses football, cricket and athletics coaching to build confidence and teamwork among young people.'),
]


def legacy_slug(title):
    return slugify(title.encode('utf-8').decode('cp1252', errors='replace'))


def asset(group, slug):
    base = Path(__file__).resolve().parents[3] / 'static' / 'img'
    for ext in ('.jpg', '.svg'):
        if (base / group / (slug+ext)).is_file():
            return 'img/'+group+'/'+slug+ext
    return 'img/hero.jpg'


def broken(value):
    """True for values damaged by an earlier UTF-8/cp1252 mix-up."""
    return isinstance(value, str) and any(marker in value for marker in ('â€', 'Ã', 'Â', '�'))


def image_missing(value):
    base = Path(__file__).resolve().parents[3] / 'static'
    return not value or not (base / value).is_file()


class Command(BaseCommand):
    help = ('Create labeled sample opportunities, journal articles and organizations. Existing rows are left '
            'untouched (so admin edits survive restarts) except for repairing broken text or missing images. '
            'Use --refresh to overwrite sample content with the bundled versions.')

    def add_arguments(self, parser):
        parser.add_argument('--refresh', action='store_true', help='Overwrite existing sample rows with bundled content.')

    def sync(self, row, values, refresh):
        if refresh:
            fields = list(values)
        else:
            fields = [k for k, v in values.items() if broken(getattr(row, k)) or (k == 'image' and image_missing(getattr(row, k)))]
        for key in fields:
            setattr(row, key, values[key])
        if fields:
            row.save(update_fields=fields)
        return bool(fields)

    @transaction.atomic
    def handle(self, *args, **options):
        refresh = options.get('refresh', False)
        created = updated = 0
        data = json.loads((Path(__file__).resolve().parents[2] / 'demo_content.json').read_text(encoding='utf-8'))
        for title, cat, city, mode, skills, summary, description in data['opportunities']:
            slug = slugify(title)
            values = dict(title=title, category=cat, city=city, mode=mode, skills=skills, summary=summary, description=description+'\n\nBefore attending, confirm training, accessibility, schedule and safety requirements with the organizer. This is a demonstration role, not a real confirmed event.', commitment='2–4 hours/week', image=asset('opportunities', slug))
            row = Opportunity.objects.filter(demo=True, slug=slug).first() or Opportunity.objects.filter(demo=True, slug=legacy_slug(title)).first()
            if row:
                # Keep the existing slug and primary key to preserve links and applications.
                updated += self.sync(row, values, refresh)
            elif not Opportunity.objects.filter(slug=slug).exists():
                Opportunity.objects.create(slug=slug, **values, organization=DEMO_ORGANIZATION, slots=12, published=True, demo=True); created += 1
        for title, cat, summary, body in data['articles']:
            slug = slugify(title)
            values = dict(title=title, category=cat, summary=summary, body=body, image=asset('journal', slug))
            row = Article.objects.filter(slug=slug).first() or Article.objects.filter(slug=legacy_slug(title)).first()
            if row:
                updated += self.sync(row, values, refresh)
            else:
                Article.objects.create(slug=slug, **values); created += 1
        created += self.seed_organizations(refresh)
        self.stdout.write(self.style.SUCCESS(f'Demo content ready ({created} created, {updated} repaired/refreshed).'))

    def seed_organizations(self, refresh):
        from community.models import Organization
        from core.models import Profile
        User = get_user_model()
        created = 0
        for name, city, causes, bio in DEMO_ORGANIZATIONS:
            slug = slugify(name)
            # Inactive placeholder owner: cannot sign in and receives no notifications.
            user, made = User.objects.get_or_create(username='sample-org-'+slug[:120], defaults={'is_active': False, 'first_name': name.replace(' (Sample)', '')[:150]})
            if made:
                user.set_unusable_password(); user.save(update_fields=['password'])
            Profile.objects.get_or_create(user=user, defaults={'role': 'organizer', 'city': city})
            org = Organization.objects.filter(owner=user).first()
            values = dict(name=name, city=city, bio=bio+SAMPLE_NOTE, public=True)
            if not org:
                if Organization.objects.filter(slug=slug).exists():
                    continue
                Organization.objects.create(owner=user, slug=slug, verified=False, **values); created += 1
            elif refresh:
                for key, value in values.items(): setattr(org, key, value)
                org.save(update_fields=list(values))
            # Attach unowned sample listings for these causes so listing <-> organization links work.
            for o in Opportunity.objects.filter(demo=True, owner__isnull=True, category__in=causes):
                o.owner = user
                if o.organization == DEMO_ORGANIZATION: o.organization = name
                o.save(update_fields=['owner', 'organization'])
        return created
