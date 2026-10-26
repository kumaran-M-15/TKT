import threading

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import connection

from .models import Booking
from .ticket_image import render_ticket


def _send(booking_id, kind):
    try:
        b = (Booking.objects
             .select_related("user", "show__movie", "show__screen__theatre")
             .prefetch_related("items__seat").get(pk=booking_id))
        if not b.user.email:
            return
        seats = ", ".join(f"{i.seat.row_label}{i.seat.number}" for i in b.items.all())
        when = f"{b.show.start_time.astimezone():%a %d %b %Y, %I:%M %p}"
        if kind == "HELD":
            by = f"{b.hold_expires_at.astimezone():%I:%M %p}"
            subject = f"Seats held for {b.show.movie.title} - pay at the counter before {by}"
            body = (f"Hi {b.user.name or 'there'},\n\n"
                    f"Your seats are held, not paid yet.\n\n"
                    f"Movie: {b.show.movie.title}\nTheatre: {b.show.screen.theatre.name}, {b.show.screen.name}\n"
                    f"Show: {when}\nSeats: {seats}\nAmount to pay at the counter: Rs {b.total_amount}\n"
                    f"Booking code: {b.booking_code}\n\n"
                    f"Show the attached ticket (or the QR on My tickets) at the counter and pay before {by}, "
                    f"or the seats are released. There is no booking fee.\n")
        else:
            subject = f"Payment received - your ticket for {b.show.movie.title}"
            body = (f"Hi {b.user.name or 'there'},\n\n"
                    f"The theatre has received your payment of Rs {b.total_amount}. Your seats are confirmed.\n\n"
                    f"Movie: {b.show.movie.title}\nTheatre: {b.show.screen.theatre.name}, {b.show.screen.name}\n"
                    f"Show: {when}\nSeats: {seats}\nBooking code: {b.booking_code}\n\n"
                    f"Your ticket is attached. Enjoy the movie!\n")
        msg = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [b.user.email])
        msg.attach(f"ticket-{b.booking_code}.png", render_ticket(b), "image/png")
        msg.send()
    except Exception as e:                       # an email problem must never break a booking
        print("Email failed:", e)
    finally:
        connection.close()


def send_ticket_email(booking_id, kind):
    """kind: 'HELD' or 'CONFIRMED'. Runs in the background so the request is not slowed down."""
    threading.Thread(target=_send, args=(booking_id, kind), daemon=True).start()