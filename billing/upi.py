"""Generates a real, scannable UPI payment QR code (the standard
`upi://pay` deep link that GPay/PhonePe/Paytm/BHIM all recognize) — no
external service or API key required."""
import io
from urllib.parse import quote

import qrcode
from django.conf import settings


def build_upi_uri(amount, note: str) -> str:
    params = (
        f'pa={quote(settings.UPI_ID)}'
        f'&pn={quote(settings.UPI_PAYEE_NAME)}'
        f'&am={amount}'
        f'&cu=INR'
        f'&tn={quote(note)}'
    )
    return f'upi://pay?{params}'


def render_qr_png(data: str) -> bytes:
    img = qrcode.make(data, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()
