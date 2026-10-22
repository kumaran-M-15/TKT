from string import ascii_uppercase
from django.core.management.base import BaseCommand, CommandError
from theatres.models import Screen, Seat


class Command(BaseCommand):
    help = "Generate a seat layout. Example: generate_seats 1 --rows 10 --per-row 12 --premium-rows 2"

    def add_arguments(self, parser):
        parser.add_argument("screen_id", type=int)
        parser.add_argument("--rows", type=int, default=10)
        parser.add_argument("--per-row", type=int, default=12)
        parser.add_argument("--premium-rows", type=int, default=2,
                            help="Last N rows become PREMIUM (back of the hall)")

    def handle(self, *args, **o):
        try:
            screen = Screen.objects.get(id=o["screen_id"])
        except Screen.DoesNotExist:
            raise CommandError("Screen not found")
        if o["rows"] > 26:
            raise CommandError("Max 26 rows")
        if screen.seats.exists():
            raise CommandError("This screen already has seats")

        seats = []
        for i in range(o["rows"]):
            seat_type = "PREMIUM" if i >= o["rows"] - o["premium_rows"] else "STANDARD"
            for n in range(1, o["per_row"] + 1):
                seats.append(Seat(screen=screen, row_label=ascii_uppercase[i], number=n, seat_type=seat_type))
        Seat.objects.bulk_create(seats)
        self.stdout.write(self.style.SUCCESS(f"Created {len(seats)} seats for {screen}"))