import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from solcx import compile_standard, install_solc
from web3 import Web3


ROOT_DIR = Path(__file__).resolve().parent
CONTRACT_FILE = ROOT_DIR / "smart_contract" / "ImageVerification.sol"
ARTIFACT_FILE = ROOT_DIR / "smart_contract" / "ImageVerification.json"
OUTPUT_FILE = ROOT_DIR / "deployed_contract_address.txt"
ENV_FILE = ROOT_DIR / "backend" / ".env"
SOLC_VERSION = "0.8.0"

load_dotenv(ENV_FILE)


def compile_contract(contract_path: Path = CONTRACT_FILE) -> tuple[list, str]:
    if not contract_path.exists():
        raise FileNotFoundError(f"Contract file not found: {contract_path}")

    install_solc(SOLC_VERSION)
    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": {
                contract_path.name: {
                    "content": contract_path.read_text(encoding="utf-8")
                }
            },
            "settings": {
                "outputSelection": {
                    "*": {"*": ["abi", "evm.bytecode"]}
                }
            },
        },
        solc_version=SOLC_VERSION,
    )
    contract_data = compiled["contracts"][contract_path.name]["ImageVerification"]
    return contract_data["abi"], contract_data["evm"]["bytecode"]["object"]


def write_artifact(abi: list) -> None:
    artifact = {
        "contractName": "ImageVerification",
        "sourceName": CONTRACT_FILE.name,
        "solcVersion": SOLC_VERSION,
        "abi": abi,
    }
    ARTIFACT_FILE.write_text(
        json.dumps(artifact, indent=2) + "\n",
        encoding="utf-8",
    )


def get_web3_provider(provider_url: str) -> Web3:
    w3 = Web3(Web3.HTTPProvider(provider_url))
    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to Ganache at {provider_url}")
    return w3


def deploy_contract(
    abi: list,
    bytecode: str,
    w3: Web3,
    private_key: str | None = None,
) -> tuple[str, str, int]:
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    if private_key:
        account = w3.eth.account.from_key(private_key)
        transaction = contract.constructor().build_transaction(
            {
                "from": account.address,
                "nonce": w3.eth.get_transaction_count(account.address),
                "gasPrice": w3.eth.gas_price,
                "gas": 3_000_000,
                "chainId": w3.eth.chain_id,
            }
        )
        signed = account.sign_transaction(transaction)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    else:
        accounts = w3.eth.accounts
        if not accounts:
            raise ValueError(
                "No unlocked Ganache accounts are available. "
                "Set DEPLOYER_PRIVATE_KEY or unlock an account."
            )
        tx_hash = contract.constructor().transact(
            {"from": accounts[0], "gas": 3_000_000}
        )

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status != 1:
        raise RuntimeError("Contract deployment transaction failed.")
    return receipt.contractAddress, receipt.transactionHash.hex(), receipt.blockNumber


def save_contract_address(address: str) -> None:
    OUTPUT_FILE.write_text(address + "\n", encoding="utf-8")


def update_env_contract_address(address: str) -> None:
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    updated = False
    output = []
    for line in lines:
        if line.startswith("CONTRACT_ADDRESS="):
            output.append(f"CONTRACT_ADDRESS={address}")
            updated = True
        else:
            output.append(line)
    if not updated:
        output.append(f"CONTRACT_ADDRESS={address}")
    ENV_FILE.write_text("\n".join(output) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile and deploy ImageVerification.sol to Ganache."
    )
    parser.add_argument(
        "--compile-only",
        action="store_true",
        help="Compile and refresh the ABI artifact without deploying.",
    )
    parser.add_argument(
        "--update-env",
        action="store_true",
        help="Update only CONTRACT_ADDRESS in backend/.env after deployment.",
    )
    args = parser.parse_args()

    provider_url = os.getenv("GANACHE_URL", "http://127.0.0.1:7545")
    private_key = os.getenv("DEPLOYER_PRIVATE_KEY") or None

    try:
        print("Compiling ImageVerification.sol")
        abi, bytecode = compile_contract()
        write_artifact(abi)
        print(f"ABI artifact: {ARTIFACT_FILE}")
        if args.compile_only:
            print("Compilation completed successfully.")
            return

        print(f"Ganache RPC: {provider_url}")
        w3 = get_web3_provider(provider_url)
        address, transaction_hash, block_number = deploy_contract(
            abi, bytecode, w3, private_key
        )
        save_contract_address(address)
        if args.update_env:
            update_env_contract_address(address)
        print("Contract deployed successfully")
        print(f"Contract address: {address}")
        print(f"Transaction hash: {transaction_hash}")
        print(f"Block number: {block_number}")
        print(f"Address file: {OUTPUT_FILE}")
        if args.update_env:
            print("Updated CONTRACT_ADDRESS in backend/.env")
        else:
            print("Update CONTRACT_ADDRESS in backend/.env with this address.")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
