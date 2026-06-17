from PIL import Image


def text_to_bits(text: str) -> str:
    return ''.join(format(ord(char), '08b') for char in text)


def bits_to_text(bits: str) -> str:
    chars = [bits[i:i+8] for i in range(0, len(bits), 8)]
    return ''.join(chr(int(char, 2)) for char in chars if len(char) == 8)


def embed_watermark(input_path: str, output_path: str, watermark_text: str) -> None:
    image = Image.open(input_path).convert('RGB')
    pixels = image.load()
    watermark_bits = text_to_bits(watermark_text)
    width, height = image.size
    bit_index = 0

    for y in range(height):
        for x in range(width):
            if bit_index >= len(watermark_bits):
                image.save(output_path)
                return
            r, g, b = pixels[x, y]
            r = (r & ~1) | int(watermark_bits[bit_index])
            pixels[x, y] = (r, g, b)
            bit_index += 1
    image.save(output_path)


def extract_watermark(image_path: str, watermark_length_chars: int) -> str:
    image = Image.open(image_path).convert('RGB')
    pixels = image.load()
    width, height = image.size
    total_bits = watermark_length_chars * 8
    extracted_bits = ''

    for y in range(height):
        for x in range(width):
            if len(extracted_bits) >= total_bits:
                return bits_to_text(extracted_bits)
            r, g, b = pixels[x, y]
            extracted_bits += str(r & 1)
    return bits_to_text(extracted_bits)
