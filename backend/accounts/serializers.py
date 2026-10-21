from rest_framework import serializers


class SendOTPSerializer(serializers.Serializer):
    phone = serializers.RegexField(r"^[6-9]\d{9}$", error_messages={"invalid": "Enter a valid 10-digit Indian mobile number"})


class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.RegexField(r"^[6-9]\d{9}$")
    code = serializers.CharField(max_length=6, min_length=6)
    name = serializers.CharField(max_length=100, required=False, allow_blank=True)