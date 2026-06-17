class BlockchainService:
    """Prototype blockchain service.
    Replace this mock implementation with Web3.py contract calls when deploying with Ganache.
    """
    def __init__(self):
        self.records = {}

    def register_image(self, image_hash: str, watermark_id: str) -> dict:
        self.records[image_hash] = {"watermark_id": watermark_id, "exists": True}
        return {"status": "registered", "image_hash": image_hash, "watermark_id": watermark_id}

    def verify_image(self, image_hash: str) -> bool:
        return image_hash in self.records

    def get_image_data(self, image_hash: str) -> dict:
        return self.records.get(image_hash, {"exists": False})
