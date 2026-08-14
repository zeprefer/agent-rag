import zipfile
from io import BytesIO

from app.core.config import settings


class SecurityScanError(ValueError):
    pass


def scan_upload(*, filename: str, extension: str, data: bytes, content_type: str | None = None) -> None:
    if not settings.security_scan_enabled:
        return
    lower_name = filename.lower()
    lower_ext = extension.lower().lstrip(".")

    if b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!" in data:
        raise SecurityScanError("Security scan rejected EICAR test content")

    _check_magic(extension=lower_ext, data=data)

    if lower_ext == "pdf":
        _scan_pdf(data)
    if lower_ext in {"docx", "xlsx", "pptx"}:
        _scan_zip_office(data)
    if lower_name.endswith((".docm", ".xlsm", ".pptm")):
        raise SecurityScanError("Macro-enabled Office files are not allowed")


def _check_magic(*, extension: str, data: bytes) -> None:
    signatures = {
        "pdf": [b"%PDF"],
        "docx": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
        "doc": [b"\xd0\xcf\x11\xe0"],
        "png": [b"\x89PNG\r\n\x1a\n"],
        "jpg": [b"\xff\xd8\xff"],
        "jpeg": [b"\xff\xd8\xff"],
        "webp": [b"RIFF"],
    }
    expected = signatures.get(extension)
    if not expected:
        return
    if not any(data.startswith(signature) for signature in expected):
        raise SecurityScanError(f"File content does not match .{extension} signature")


def _scan_pdf(data: bytes) -> None:
    sample = data[:2_000_000].lower()
    suspicious_tokens = [b"/javascript", b"/js", b"/openaction", b"/launch", b"/embeddedfile"]
    if any(token in sample for token in suspicious_tokens):
        raise SecurityScanError("PDF contains active or embedded content that is not allowed")


def _scan_zip_office(data: bytes) -> None:
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            names = [name.lower() for name in archive.namelist()]
    except zipfile.BadZipFile as exc:
        raise SecurityScanError("Office file is not a valid zip package") from exc

    if any("vbaproject.bin" in name for name in names):
        raise SecurityScanError("Office macros are not allowed")
    if any(name.endswith(".exe") or name.endswith(".dll") or name.endswith(".js") for name in names):
        raise SecurityScanError("Office package contains executable content")

