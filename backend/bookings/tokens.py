from django.core import signing

SALT = "booking-qr"


def make_qr_token(booking):
    return signing.dumps({"b": str(booking.id), "n": booking.qr_nonce}, salt=SALT)


def read_qr_token(token):
    # no max_age: validity comes from booking status and expiry, not token age
    return signing.loads(token, salt=SALT)