import json
import os
from pathlib import Path

from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import ContractLogicError


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ABI_PATH = ROOT_DIR / "smart_contract" / "ImageVerification.json"
DEFAULT_PROVIDER = "http://127.0.0.1:7545"
load_dotenv(Path(__file__).resolve().parent / ".env")


class BlockchainService:
    def __init__(
        self,
        provider_url: str | None = None,
        contract_address: str | None = None,
        abi_path: str | Path | None = None,
    ):
        self.provider_url = provider_url or os.getenv("GANACHE_URL", DEFAULT_PROVIDER)
        self.contract_address = contract_address or os.getenv("CONTRACT_ADDRESS", "")
        self.abi_path = Path(abi_path or os.getenv("CONTRACT_ABI_PATH", DEFAULT_ABI_PATH))
        self.w3 = Web3(Web3.HTTPProvider(self.provider_url))
        self.contract = None
        self.default_account = ""

    def _connect(self) -> dict:
        if not self.w3.is_connected():
            return {
                "ok": False,
                "error": f"Unable to connect to Ganache at {self.provider_url}.",
            }
        if not self.contract_address:
            return {
                "ok": False,
                "error": "CONTRACT_ADDRESS is not configured.",
            }
        if not self.abi_path.exists():
            return {
                "ok": False,
                "error": f"Contract ABI not found at {self.abi_path}.",
            }

        try:
            artifact = json.loads(self.abi_path.read_text(encoding="utf-8"))
            abi = artifact["abi"] if isinstance(artifact, dict) else artifact
            self.contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(self.contract_address),
                abi=abi,
            )
            accounts = self.w3.eth.accounts
            if not accounts:
                return {
                    "ok": False,
                    "error": "No unlocked Ganache accounts are available.",
                }
            self.default_account = accounts[0]
            self.contract.functions.verifyImage(
                "0" * 64
            ).call()
            return {"ok": True}
        except Exception as exc:
            self.contract = None
            return {"ok": False, "error": f"Blockchain configuration failed: {exc}"}

    def health(self) -> dict:
        connection = self._connect()
        if not connection["ok"]:
            return {
                "ok": False,
                "provider_url": self.provider_url,
                "contract_address": self.contract_address,
                "error": connection["error"],
            }
        return {
            "ok": True,
            "provider_url": self.provider_url,
            "contract_address": self.contract_address,
            "account": self.default_account,
            "chain_id": self.w3.eth.chain_id,
            "block_number": self.w3.eth.block_number,
        }

    def register_image(self, image_hash: str, watermark_id: str) -> dict:
        connection = self._connect()
        if not connection["ok"]:
            return {"ok": False, "error": connection["error"]}

        try:
            tx_hash = self.contract.functions.registerImage(
                image_hash, watermark_id
            ).transact({"from": self.default_account})
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            if receipt.status != 1:
                return {"ok": False, "error": "Blockchain transaction failed."}
            return {
                "ok": True,
                "image_hash": image_hash,
                "watermark_id": watermark_id,
                "transaction_hash": receipt.transactionHash.hex(),
                "contract_address": self.contract_address,
                "block_number": receipt.blockNumber,
            }
        except ContractLogicError as exc:
            return {"ok": False, "error": f"Registration rejected: {exc}"}
        except Exception as exc:
            return {"ok": False, "error": f"Blockchain registration failed: {exc}"}

    def verify_image(self, image_hash: str) -> dict:
        data = self.get_image_data(image_hash)
        if not data["ok"]:
            return data
        return {"ok": True, "exists": data["exists"]}

    def get_image_data(self, image_hash: str) -> dict:
        connection = self._connect()
        if not connection["ok"]:
            return {"ok": False, "exists": False, "error": connection["error"]}

        try:
            raw = self.contract.functions.getImageData(image_hash).call()
            return {
                "ok": True,
                "image_hash": raw[0],
                "watermark_id": raw[1],
                "creator": raw[2],
                "timestamp": raw[3],
                "exists": raw[4],
            }
        except Exception as exc:
            return {
                "ok": False,
                "exists": False,
                "error": f"Blockchain lookup failed: {exc}",
            }
