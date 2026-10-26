import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import ProtectedError

from theatres.models import Screen, Seat


class Command(BaseCommand):
    help = "Build a screen's seat layout from a text file."

    def add_arguments(self, parser):
        parser.add_argument("screen_id", type=int)
        parser.add_argument("file")
        parser.add_argument("--replace", action="store_true", help="Delete the existing seats first")

    @transaction.atomic
    def handle(self, *args, **o):
        try:
            screen = Screen.objects.get(id=o["screen_id"])
        except Screen.DoesNotExist:
            raise CommandError("Screen not found")

        if screen.seats.exists():
            if not o["replace"]:
                raise CommandError("Screen already has seats. Use --replace")
            try:
                screen.seats.all().delete()
            except ProtectedError:
                raise CommandError("Seats are used by bookings. Delete the test bookings in the admin first")

        seat_type, seats, counts = None, [], {}
        with open(o["file"], encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = re.fullmatch(r"\[(.+)\]", line)
                if m:
                    seat_type = m.group(1).strip().upper()
                    continue
                if "|" not in line or not seat_type:
                    raise CommandError(f"Line {n}: expected ROW|pattern under a [SECTION]")
                row, pattern = line.split("|", 1)
                row, number = row.strip().upper(), 0
                for col, ch in enumerate(pattern.strip()):
                    if ch.upper() == "X":
                        number += 1
                        seats.append(Seat(screen=screen, row_label=row, number=number,
                                          col=col, seat_type=seat_type))
                        counts[seat_type] = counts.get(seat_type, 0) + 1

        Seat.objects.bulk_create(seats)
        self.stdout.write(self.style.SUCCESS(f"Created {len(seats)} seats: {counts}"))