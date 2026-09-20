from django.core.management.base import BaseCommand

from builder.models import Template
from builder.services.template_ingest import _parametrize_theme_color


class Command(BaseCommand):
    help = (
        "Retroactively runs the dominant-accent-color detection/CSS rewrite "
        "(services.template_ingest._parametrize_theme_color) against every "
        "Template that doesn't have one yet — for templates uploaded before "
        "that feature existed, whose CSS was never given the "
        "var(--vicinic-primary, ...) treatment, so a Site's own primary_color "
        "override currently has nothing to hook into and silently does nothing."
    )

    def handle(self, *args, **options):
        templates = Template.objects.filter(default_primary_color="")
        if not templates:
            self.stdout.write("Every template already has a default_primary_color — nothing to do.")
            return
        for template in templates:
            _parametrize_theme_color(template)
            template.refresh_from_db()
            result = template.default_primary_color or "(none confidently detected)"
            self.stdout.write(f"{template.slug}: {result}")
