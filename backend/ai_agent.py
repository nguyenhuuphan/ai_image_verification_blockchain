try:
    from .hash_utils import generate_sha256_hash
    from .watermark import extract_watermark
except ImportError:
    from hash_utils import generate_sha256_hash
    from watermark import extract_watermark


class ImageVerificationAgent:
    def __init__(self, blockchain_service):
        self.blockchain_service = blockchain_service

    @staticmethod
    def _result(
        status: str,
        message: str,
        recommendation: str,
        image_hash: str = "",
        watermark: str = "",
        blockchain_status: str = "Not checked",
        chain_data: dict | None = None,
    ) -> dict:
        return {
            "status": status,
            "message": message,
            "recommendation": recommendation,
            "image_hash": image_hash,
            "watermark_status": "Found" if watermark else "Not found",
            "watermark": watermark,
            "blockchain_status": blockchain_status,
            "chain_data": chain_data or {},
        }

    def verify_image(self, image_path: str) -> dict:
        try:
            image_hash = generate_sha256_hash(image_path)
            watermark_text = extract_watermark(image_path)
        except Exception as exc:
            return self._result(
                "Verification Failed",
                f"Verification failed because the image could not be processed: {exc}",
                "Check the file and try a supported PNG, JPG, or JPEG image.",
            )

        blockchain_data = self.blockchain_service.get_image_data(image_hash)
        if not blockchain_data.get("ok", False):
            return self._result(
                "Verification Failed",
                blockchain_data.get("error", "Blockchain lookup could not be completed."),
                "Start Ganache, confirm the contract address, and try again.",
                image_hash=image_hash,
                watermark=watermark_text,
                blockchain_status="Lookup failed",
            )

        if blockchain_data.get("exists"):
            expected_watermark = blockchain_data.get("watermark_id", "")
            if watermark_text and watermark_text == expected_watermark:
                return self._result(
                    "Authentic",
                    "The watermark was extracted and the exact image hash was found on blockchain.",
                    "Keep this registered watermarked image as the official version.",
                    image_hash=image_hash,
                    watermark=watermark_text,
                    blockchain_status="Found",
                    chain_data=blockchain_data,
                )
            return self._result(
                "Suspicious",
                "The image hash exists on blockchain, but the expected watermark could not be confirmed.",
                "Review the file and registration metadata before trusting it.",
                image_hash=image_hash,
                watermark=watermark_text,
                blockchain_status="Found",
                chain_data=blockchain_data,
            )

        if watermark_text:
            return self._result(
                "Modified",
                "A valid watermark exists, but the exact image hash is not registered.",
                "Treat this as a changed copy; register it separately only if it should become official.",
                image_hash=image_hash,
                watermark=watermark_text,
                blockchain_status="Not found",
                chain_data=blockchain_data,
            )

        return self._result(
            "Unknown",
            "No valid watermark or blockchain registration was found for this image.",
            "Do not treat the image as verified by this prototype.",
            image_hash=image_hash,
            blockchain_status="Not found",
            chain_data=blockchain_data,
        )
