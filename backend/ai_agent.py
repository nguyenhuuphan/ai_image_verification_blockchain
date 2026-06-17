from hash_utils import generate_sha256_hash
from watermark import extract_watermark


class ImageVerificationAgent:
    def __init__(self, blockchain_service):
        self.blockchain_service = blockchain_service

    def verify_image(self, image_path: str, watermark_length: int = 12) -> dict:
        image_hash = generate_sha256_hash(image_path)
        watermark_text = extract_watermark(image_path, watermark_length)
        blockchain_result = self.blockchain_service.verify_image(image_hash)

        if blockchain_result and watermark_text.strip():
            return {
                "status": "Authentic",
                "message": "The image watermark and blockchain record are valid.",
                "image_hash": image_hash,
                "watermark": watermark_text
            }
        if watermark_text.strip() and not blockchain_result:
            return {
                "status": "Modified",
                "message": "A watermark exists but the blockchain hash does not match.",
                "image_hash": image_hash,
                "watermark": watermark_text
            }
        return {
            "status": "Unknown",
            "message": "No valid watermark or blockchain record was found.",
            "image_hash": image_hash,
            "watermark": watermark_text
        }
