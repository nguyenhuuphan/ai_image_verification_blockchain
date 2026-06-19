import re
from pathlib import Path

from PIL import Image


# The research uses red-channel LSB watermarking. A small marker and length
# header make extraction reliable without changing the basic method.
WATERMARK_MARKER = b"AIVB"
WATERMARK_VERSION = 1
WATERMARK_PATTERN = re.compile(r"^WMK-\d{4}-[A-F0-9]{8}$")
HEADER_LENGTH = len(WATERMARK_MARKER) + 1 + 2


def _to_bits(data: bytes) -> str:
    return "".join(f"{byte:08b}" for byte in data)


def _to_bytes(bits: list[str]) -> bytes:
    joined = "".join(bits)
    return bytes(
        int(joined[index:index + 8], 2)
        for index in range(0, len(joined), 8)
        if len(joined[index:index + 8]) == 8
    )


def is_valid_watermark(watermark_text: str) -> bool:
    return bool(WATERMARK_PATTERN.fullmatch(watermark_text or ""))


def embed_watermark(input_path: str, output_path: str, watermark_text: str) -> None:
    """Embed a watermark in the red-channel LSBs of an RGB PNG."""
    if not is_valid_watermark(watermark_text):
        raise ValueError("Watermark ID must use the format WMK-YYYY-XXXXXXXX.")

    watermark_bytes = watermark_text.encode("utf-8")
    payload = (
        WATERMARK_MARKER
        + bytes([WATERMARK_VERSION])
        + len(watermark_bytes).to_bytes(2, "big")
        + watermark_bytes
    )
    payload_bits = _to_bits(payload)

    with Image.open(input_path) as source:
        image = source.convert("RGB")

    width, height = image.size
    capacity = width * height
    if len(payload_bits) > capacity:
        raise ValueError(
            f"Image too small for watermark. Need {len(payload_bits)} pixels "
            f"but image capacity is {capacity} pixels."
        )

    pixels = image.load()
    bit_index = 0
    for y in range(height):
        for x in range(width):
            if bit_index == len(payload_bits):
                break
            red, green, blue = pixels[x, y]
            red = (red & ~1) | int(payload_bits[bit_index])
            pixels[x, y] = (red, green, blue)
            bit_index += 1
        if bit_index == len(payload_bits):
            break

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")


def extract_watermark(image_path: str) -> str:
    """Read and validate a watermark from red-channel LSBs."""
    try:
        with Image.open(image_path) as source:
            image = source.convert("RGB")
    except (OSError, ValueError):
        return ""

    width, height = image.size
    pixels = image.load()
    header_bits = HEADER_LENGTH * 8
    bits: list[str] = []
    total_bits = None

    for y in range(height):
        for x in range(width):
            red, _green, _blue = pixels[x, y]
            bits.append(str(red & 1))

            if len(bits) == header_bits:
                header = _to_bytes(bits)
                marker_end = len(WATERMARK_MARKER)
                if header[:marker_end] != WATERMARK_MARKER:
                    return ""
                if header[marker_end] != WATERMARK_VERSION:
                    return ""

                watermark_length = int.from_bytes(header[-2:], "big")
                if watermark_length <= 0:
                    return ""
                total_bits = header_bits + watermark_length * 8
                if total_bits > width * height:
                    return ""

            if total_bits is not None and len(bits) == total_bits:
                watermark_bytes = _to_bytes(bits[header_bits:])
                try:
                    watermark = watermark_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    return ""
                return watermark if is_valid_watermark(watermark) else ""

    return ""
