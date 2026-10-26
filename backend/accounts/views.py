from datetime import timedelta
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTP, User
from .serializers import SendOTPSerializer, VerifyOTPSerializer


class OTPThrottle(AnonRateThrottle):
    rate = "5/min"


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([OTPThrottle])
def send_otp(request):
    s = SendOTPSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    phone = s.validated_data["phone"]

    recent = OTP.objects.filter(phone=phone, created_at__gte=timezone.now() - timedelta(hours=1)).count()
    if recent >= 5:
        return Response({"error": "Too many OTP requests. Try again later."}, status=429)

    otp = OTP.generate(phone)
    print(f"\n=== DEV OTP for {phone}: {otp.code} ===\n")   # replace with SMS later

    # only a yes/no: ask for a name only if this phone has no saved name
    needs_name = not User.objects.filter(phone=phone).exclude(name="").exists()
    return Response({"message": "OTP sent", "needs_name": needs_name})


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_otp(request):
    s = VerifyOTPSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    phone, code = s.validated_data["phone"], s.validated_data["code"]

    otp = OTP.objects.filter(phone=phone, used=False).order_by("-created_at").first()
    if not otp or otp.is_expired():
        return Response({"error": "OTP expired or not found. Request a new one."}, status=400)
    if otp.attempts >= 5:
        return Response({"error": "Too many wrong attempts. Request a new OTP."}, status=429)
    if otp.code != code:
        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        return Response({"error": "Wrong OTP"}, status=400)

    otp.used = True
    otp.save(update_fields=["used"])

    user, created = User.objects.get_or_create(phone=phone)
    name = (s.validated_data.get("name") or "").strip()
    if name and not user.name:                     # saved once, in the database
        user.name = name
        user.save(update_fields=["name"])

    refresh = RefreshToken.for_user(user)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {"id": user.id, "phone": user.phone, "name": user.name, "role": user.role},
        "new_user": created,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    u = request.user
    return Response({
        "id": u.id, "phone": u.phone, "name": u.name, "role": u.role,
        "strike_count": u.strike_count, "blocked_until": u.blocked_until,
        "can_pay_at_counter": not (u.blocked_until and u.blocked_until > timezone.now()),
    })