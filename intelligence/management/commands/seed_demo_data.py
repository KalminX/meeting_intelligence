"""
Management command to seed realistic demo data into Meeting Intelligence.
"""
from django.core.management.base import BaseCommand
from intelligence.services.seed_service import SeedService


class Command(BaseCommand):
    help = 'Seeds realistic enterprise demo data for Meeting Intelligence'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Reseeding Meeting Intelligence demo environment..."))
        result = SeedService.reseed_all_demo_data()
        self.stdout.write(self.style.SUCCESS(
            f"Successfully reseeded: {result['clients_created']} clients, "
            f"{result['meetings_created']} meetings, {result['tasks_created']} tasks, "
            f"{result['transcripts_created']} transcripts."
        ))
