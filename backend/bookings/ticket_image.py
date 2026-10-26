import io

import qrcode
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

RED = (176, 52, 56)
INK = (38, 50, 56)
WHITE = (255, 255, 255)
GREY = (110, 120, 128)
GREEN = (26, 140, 80)
AMBER = (255, 243, 205)


def _font(size, bold=False):
    names = ["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"]
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def _fit(d, text, size, max_w, bold=True):
    while size > 14:
        f = _font(size, bold)
        if d.textlength(text, font=f) <= max_w:
            return f
        size -= 2
    return _font(14, bold)


def render_ticket(b):
    """b: a Booking with show__movie, show__screen__theatre and items__seat loaded. Returns PNG bytes."""
    W, H, M, SX = 1200, 560, 40, 420
    img = Image.new("RGB", (W, H), RED)
    d = ImageDraw.Draw(img)

    seats = [f"{i.seat.row_label}{i.seat.number}" for i in b.items.all()]
    show = b.show
    start = timezone.localtime(show.start_time)

    # ticket body, header band, then notches and tear line
    d.rounded_rectangle((M, M, W - M, H - M), radius=26, fill=WHITE)
    d.rounded_rectangle((SX + 1, M, W - M, M + 84), radius=26, fill=INK, corners=(False, True, False, False))
    d.ellipse((SX - 22, M - 22, SX + 22, M + 22), fill=RED)
    d.ellipse((SX - 22, H - M - 22, SX + 22, H - M + 22), fill=RED)
    for y in range(M + 34, H - M - 20, 18):
        d.line((SX, y, SX, y + 9), fill=GREY, width=3)

    # stub: QR with the booking code
    cx = (M + SX) // 2
    d.text((cx, 90), "CINEMA TICKET", font=_font(30, True), fill=INK, anchor="mm")
    d.text((cx, 126), f"ADMIT {len(seats)}", font=_font(22), fill=GREY, anchor="mm")
    qr = qrcode.make(b.booking_code, box_size=12, border=1).get_image().convert("RGB").resize((270, 270), Image.NEAREST)
    img.paste(qr, (cx - 135, 160))
    d.text((cx, 455), "BOOKING CODE", font=_font(18), fill=GREY, anchor="mm")
    d.text((cx, 488), b.booking_code, font=_font(34, True), fill=INK, anchor="mm")

    # header band
    d.text((SX + 30, M + 42), f"NO. {str(b.id)[:8].upper()}", font=_font(22), fill=WHITE, anchor="lm")
    d.text((W - M - 30, M + 42), "MOVIE TICKET", font=_font(36, True), fill=WHITE, anchor="rm")

    # details
    x0, x1 = SX + 40, SX + 400
    d.text((x0, 125), show.movie.title, font=_fit(d, show.movie.title, 56, 660), fill=INK)
    d.text((x0, 190), " | ".join(filter(None, [show.movie.language, show.movie.certificate])),
           font=_font(22), fill=GREY)

    def field(x, y, label, value, max_w=320):
        d.text((x, y), label, font=_font(18), fill=GREY)
        d.text((x, y + 22), value, font=_fit(d, value, 30, max_w), fill=INK)

    field(x0, 230, "THEATRE", show.screen.theatre.name)
    field(x1, 230, "SCREEN", show.screen.name, 300)
    field(x0, 305, "DATE", start.strftime("%a, %d %b %Y"))
    field(x1, 305, "TIME", start.strftime("%I:%M %p"), 300)
    field(x0, 380, "SEATS", ", ".join(seats), 330)
    field(x1, 380, "AMOUNT", f"Rs {b.total_amount}", 300)

    # status bar
    if b.status == "CONFIRMED":
        mode = f" ({b.payment_mode})" if b.payment_mode else ""
        text, fill, ink = f"PAID{mode} - VALID FOR ENTRY", GREEN, WHITE
    elif b.status == "HELD":
        by = timezone.localtime(b.hold_expires_at).strftime("%I:%M %p")
        text, fill, ink = f"PAY Rs {b.total_amount} AT THE COUNTER BEFORE {by}", AMBER, INK
    else:
        text, fill, ink = b.status, GREY, WHITE
    d.rounded_rectangle((x0, 452, W - M - 40, 502), radius=12, fill=fill)
    d.text(((x0 + W - M - 40) // 2, 477), text, font=_fit(d, text, 26, 640), fill=ink, anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()