from django.apps import AppConfig
from django.db.models.signals import post_migrate


def seed_after_migrate(sender, **kwargs):
    """Create missing sample content (listings, journal, organizations) after every migrate.

    Runs create-only, so admin edits are never overwritten. This guarantees the
    Organizations directory is populated on deploy even if the start command does
    not call `seed_demo`. Disable with SEED_DEMO_ON_MIGRATE=0.
    """
    import os
    # post_migrate fires once per app; run after `community` (whose tables we need).
    if getattr(sender, 'name', '') != 'community':
        return
    if os.getenv('SEED_DEMO_ON_MIGRATE', '1') != '1' or kwargs.get('using', 'default') != 'default':
        return
    from django.core.management import call_command
    try:
        call_command('seed_demo', verbosity=0)
    except Exception:  # never block a deploy because of sample content
        import logging
        logging.getLogger(__name__).exception('Sample content seeding failed')


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Volunteering'

    def ready(self):
        # Run once, after the last app (community) has migrated.
        post_migrate.connect(seed_after_migrate, dispatch_uid='voluntr-seed-demo')
