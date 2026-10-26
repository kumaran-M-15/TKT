import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.utils import timezone

from bookings.models import Booking
from bookings.services import expire_stale_holds


class Command(BaseCommand):
    help = "Every N seconds: release unpaid holds past their cutoff (adds strikes) and complete finished shows."

    def add_arguments(self, parser):
        parser.add_argument("--every", type=int, default=60, help="Seconds between runs")
        parser.add_argument("--once", action="store_true", help="Run one pass and exit")

    def handle(self, *args, **o):
        self.stdout.write(self.style.SUCCESS(f"Expiry worker started (every {o['every']}s). Ctrl+C to stop."))
        while True:
            try:
                close_old_connections()
                expired = expire_stale_holds()
                done = Booking.objects.filter(
                    status=Booking.CONFIRMED, show__end_time__lt=timezone.now()
                ).update(status=Booking.COMPLETED)
                if expired or done:
                    self.stdout.write(f"{timezone.localtime():%H:%M:%S} expired={expired} completed={done}")
            except Exception as e:                      # keep the worker alive
                self.stderr.write(f"Expiry pass failed: {e}")
            if o["once"]:
                break
            time.sleep(o["every"])