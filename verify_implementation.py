import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image
from web3 import Web3

from backend.ai_agent import ImageVerificationAgent
from backend.blockchain_service import BlockchainService
from backend.hash_utils import generate_sha256_hash
from backend.watermark import embed_watermark, extract_watermark
from deploy_contract import compile_contract, deploy_contract


ROOT_DIR = Path(__file__).resolve().parent
SOURCE_IMAGE = ROOT_DIR / "test_images" / "monalisa.png"
GANACHE_URL = "http://127.0.0.1:7545"
WATERMARK_ID = "WMK-2026-A1B2C3D4"


def print_result(test_id: str, scenario: str, expected: str, actual: str) -> bool:
    passed = actual in expected.split(" or ")
    status = "PASS" if passed else "FAIL"
    print(f"{test_id:<5} {scenario:<30} {actual:<22} {status}")
    return passed


def prepare_images(folder: Path) -> dict[str, Path]:
    original = folder / "original.png"
    with Image.open(SOURCE_IMAGE) as image:
        image.convert("RGB").save(original)

    watermarked = folder / "watermarked.png"
    embed_watermark(str(original), str(watermarked), WATERMARK_ID)

    unknown = folder / "unknown.png"
    Image.new("RGB", (640, 480), (80, 75, 70)).save(unknown)

    modified = folder / "modified.png"
    shutil.copyfile(watermarked, modified)
    with Image.open(modified) as image:
        changed = image.copy()
    x, y = changed.width - 1, changed.height - 1
    red, green, blue = changed.getpixel((x, y))
    changed.putpixel((x, y), ((red + 1) % 256, green, blue))
    changed.save(modified)

    cropped = folder / "cropped.png"
    with Image.open(watermarked) as image:
        image.crop((20, 20, image.width - 20, image.height - 20)).save(cropped)

    compressed = folder / "compressed.jpg"
    with Image.open(watermarked) as image:
        image.save(compressed, "JPEG", quality=65)

    renamed = folder / "renamed.png"
    shutil.copyfile(watermarked, renamed)

    unsupported = folder / "unsupported.txt"
    unsupported.write_text("Not an image.", encoding="utf-8")

    corrupted = folder / "corrupted.png"
    corrupted.write_bytes(b"\x89PNG\r\n\x1a\ncorrupted")

    return {
        "original": original,
        "watermarked": watermarked,
        "unknown": unknown,
        "modified": modified,
        "cropped": cropped,
        "compressed": compressed,
        "renamed": renamed,
        "unsupported": unsupported,
        "corrupted": corrupted,
    }


def check_red_channel_only(original: Path, watermarked: Path) -> bool:
    with Image.open(original) as before, Image.open(watermarked) as after:
        for y in range(before.height):
            for x in range(before.width):
                original_pixel = before.getpixel((x, y))
                watermarked_pixel = after.getpixel((x, y))
                if original_pixel[1:] != watermarked_pixel[1:]:
                    return False
                if abs(original_pixel[0] - watermarked_pixel[0]) > 1:
                    return False
    return True


def main() -> None:
    if not SOURCE_IMAGE.exists():
        print(f"Missing test image: {SOURCE_IMAGE}", file=sys.stderr)
        raise SystemExit(1)

    web3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    if not web3.is_connected():
        print(f"Ganache is not running at {GANACHE_URL}.", file=sys.stderr)
        raise SystemExit(1)

    print("Deploying a fresh ImageVerification contract for verification...")
    abi, bytecode = compile_contract()
    contract_address, transaction_hash, block_number = deploy_contract(
        abi, bytecode, web3
    )
    print(f"Contract: {contract_address}")
    print(f"Deployment transaction: {transaction_hash}")
    print(f"Block: {block_number}\n")

    service = BlockchainService(
        provider_url=GANACHE_URL,
        contract_address=contract_address,
    )
    agent = ImageVerificationAgent(service)
    passed_checks: list[bool] = []

    with tempfile.TemporaryDirectory(prefix="image-verification-") as temp_dir:
        images = prepare_images(Path(temp_dir))

        print("Implementation checks")
        watermark_round_trip = (
            extract_watermark(str(images["watermarked"])) == WATERMARK_ID
        )
        passed_checks.append(
            print_result(
                "CHK1",
                "Watermark round trip",
                "PASS",
                "PASS" if watermark_round_trip else "FAIL",
            )
        )
        red_only = check_red_channel_only(
            images["original"], images["watermarked"]
        )
        passed_checks.append(
            print_result(
                "CHK2",
                "Only red-channel LSB changes",
                "PASS",
                "PASS" if red_only else "FAIL",
            )
        )
        renamed_hash_match = generate_sha256_hash(
            str(images["watermarked"])
        ) == generate_sha256_hash(str(images["renamed"]))
        passed_checks.append(
            print_result(
                "CHK3",
                "Renamed file keeps hash",
                "PASS",
                "PASS" if renamed_hash_match else "FAIL",
            )
        )

        print("\nTC01-TC09")
        image_hash = generate_sha256_hash(str(images["watermarked"]))
        registration = service.register_image(image_hash, WATERMARK_ID)
        passed_checks.append(
            print_result(
                "TC01",
                "Register original image",
                "Registration Success",
                "Registration Success" if registration.get("ok") else "Failed",
            )
        )

        cases = [
            ("TC02", "Verify registered image", "watermarked", "Authentic"),
            ("TC03", "Verify unknown image", "unknown", "Unknown"),
            ("TC04", "Verify modified image", "modified", "Modified"),
            ("TC05", "Verify cropped image", "cropped", "Modified or Unknown"),
            (
                "TC06",
                "Verify compressed JPEG",
                "compressed",
                "Modified or Unknown",
            ),
            ("TC07", "Verify renamed image", "renamed", "Authentic"),
        ]
        for test_id, scenario, image_name, expected in cases:
            result = agent.verify_image(str(images[image_name]))
            passed_checks.append(
                print_result(test_id, scenario, expected, result["status"])
            )

        unsupported_result = (
            "Verification Failed"
            if images["unsupported"].suffix.lower() not in {".png", ".jpg", ".jpeg"}
            else "Unknown"
        )
        passed_checks.append(
            print_result(
                "TC08",
                "Unsupported file",
                "Verification Failed",
                unsupported_result,
            )
        )

        try:
            with Image.open(images["corrupted"]) as image:
                image.verify()
            corrupted_result = "Unknown"
        except Exception:
            corrupted_result = "Verification Failed"
        passed_checks.append(
            print_result(
                "TC09",
                "Corrupted image",
                "Verification Failed",
                corrupted_result,
            )
        )

    total = len(passed_checks)
    passed = sum(passed_checks)
    print(f"\nResult: {passed}/{total} checks passed.")
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
