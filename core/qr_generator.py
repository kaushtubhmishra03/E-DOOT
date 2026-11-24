import io
import base64
import qrcode
from typing import Optional


def generate_qr_code_data_url(data_payload: str, box_size: int = 10, border: int = 2) -> str:
    """
    Generate a base64 Data URL for a QR code image encoding the given payload.
    Supports high error correction so scanning works under glare or screen damage.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data_payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_img = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_img}"


def build_emergency_qr_payload(base_url: str, qr_uuid: str, offline_summary: Optional[str] = None) -> str:
    """
    Creates the QR code payload.
    By default links to the web emergency summary route.
    """
    target_url = f"{base_url.rstrip('/')}/app/emergency/{qr_uuid}"
    return target_url


def format_offline_medical_card(
    full_name: str,
    blood_group: str,
    allergies: str,
    conditions: str,
    emergency_contact: str,
    web_url: str
) -> str:
    """
    Creates a compact offline text vCard / Emergency text string.
    If scanned by standard camera or offline QR reader, vital info is immediately visible.
    """
    lines = [
        "*** E-DOOT EMERGENCY MEDICAL ID ***",
        f"PATIENT: {full_name}",
        f"BLOOD GROUP: {blood_group or 'Unknown'}",
    ]
    if allergies:
        lines.append(f"ALLERGIES: {allergies}")
    if conditions:
        lines.append(f"CONDITIONS: {conditions}")
    if emergency_contact:
        lines.append(f"ICE CONTACT: {emergency_contact}")
    lines.append(f"LIVE AID PORTAL: {web_url}")
    return "\n".join(lines)
