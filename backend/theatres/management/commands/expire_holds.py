from django.core.management.base import BaseCommand
from bookings.services import expire_stale_holds


class Command(BaseCommand):
    help = "Release unpaid holds past their cutoff and add strikes"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"Expired {expire_stale_holds()} holds"))