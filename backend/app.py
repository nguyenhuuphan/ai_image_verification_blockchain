import os
import secrets
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request, send_from_directory
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

try:
    from .ai_agent import ImageVerificationAgent
    from .blockchain_service import BlockchainService
    from .config import ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH, UPLOAD_DIR
    from .hash_utils import generate_sha256_hash
    from .watermark import embed_watermark
except ImportError:
    from ai_agent import ImageVerificationAgent
    from blockchain_service import BlockchainService
    from config import ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH, UPLOAD_DIR
    from hash_utils import generate_sha256_hash
    from watermark import embed_watermark


load_dotenv(Path(__file__).resolve().parent / ".env")


def generate_watermark_id(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return f"WMK-{current.year}-{secrets.token_hex(4).upper()}"


def format_timestamp(timestamp: int | str | None) -> str:
    try:
        value = int(timestamp or 0)
    except (TypeError, ValueError):
        return ""
    if value <= 0:
        return ""
    return datetime.fromtimestamp(value, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


def _failure(message: str, recommendation: str) -> dict:
    return {
        "status": "Verification Failed",
        "message": message,
        "recommendation": recommendation,
        "watermark_status": "Not processed",
        "blockchain_status": "Not checked",
    }


def _validate_upload(file_storage) -> tuple[bool, str]:
    if not file_storage or not file_storage.filename:
        return False, "No image was uploaded."
    suffix = Path(secure_filename(file_storage.filename)).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return False, "Only PNG, JPG, and JPEG image files are supported."
    return True, ""


def _validate_image(path: Path) -> None:
    with Image.open(path) as image:
        image.verify()


def create_app(blockchain_service=None, test_config: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder="../frontend",
        static_folder="../frontend/static",
    )
    app.config.update(
        MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH,
        UPLOAD_DIR=UPLOAD_DIR,
        TESTING=False,
    )
    if test_config:
        app.config.update(test_config)

    upload_dir = Path(app.config["UPLOAD_DIR"]).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    service = blockchain_service or BlockchainService()
    agent = ImageVerificationAgent(service)
    app.extensions["blockchain_service"] = service
    app.extensions["verification_agent"] = agent

    @app.context_processor
    def template_helpers():
        return {"format_timestamp": format_timestamp}

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_error):
        return render_template(
            "result.html",
            result=_failure(
                "Verification failed because the uploaded file exceeds the 16 MB limit.",
                "Choose a smaller PNG, JPG, or JPEG image.",
            ),
        ), 413

    @app.route("/")
    def index():
        health = service.health()
        return render_template("index.html", blockchain_health=health)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "GET":
            return render_template("register.html")

        image = request.files.get("image")
        valid, error = _validate_upload(image)
        if not valid:
            return render_template(
                "result.html",
                result=_failure(error, "Choose a supported image and try again."),
            ), 400

        original_name = secure_filename(image.filename)
        suffix = Path(original_name).suffix.lower()
        watermark_id = generate_watermark_id()
        output_name = f"watermarked_{watermark_id.lower()}.png"
        output_path = upload_dir / output_name

        try:
            with tempfile.TemporaryDirectory(prefix="aivb-register-") as temp_dir:
                source_path = Path(temp_dir) / f"source{suffix}"
                image.save(source_path)
                _validate_image(source_path)

                prepared_path = Path(temp_dir) / "prepared.png"
                with Image.open(source_path) as source:
                    source.convert("RGB").save(prepared_path, format="PNG")
                embed_watermark(
                    str(prepared_path), str(output_path), watermark_id
                )
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            output_path.unlink(missing_ok=True)
            return render_template(
                "result.html",
                result=_failure(
                    f"Verification failed because the image could not be processed: {exc}",
                    "Choose a readable PNG, JPG, or JPEG image.",
                ),
            ), 400

        image_hash = generate_sha256_hash(str(output_path))
        registration = service.register_image(image_hash, watermark_id)
        if not registration.get("ok"):
            output_path.unlink(missing_ok=True)
            return render_template(
                "result.html",
                result=_failure(
                    registration.get("error", "Blockchain registration failed."),
                    "Start Ganache, verify the deployed contract address, and try again.",
                )
                | {
                    "image_hash": image_hash,
                    "watermark": watermark_id,
                    "watermark_status": "Embedded",
                    "blockchain_status": "Registration failed",
                },
            ), 503

        chain_data = service.get_image_data(image_hash)
        result = {
            "status": "Registration Success",
            "message": "The watermarked image hash and metadata were registered on blockchain.",
            "recommendation": "Download and keep the watermarked PNG as the official verifiable copy.",
            "image_hash": image_hash,
            "watermark_status": "Embedded",
            "watermark": watermark_id,
            "blockchain_status": "Registered",
            "transaction_hash": registration["transaction_hash"],
            "contract_address": registration["contract_address"],
            "block_number": registration.get("block_number"),
            "registered_image": output_name,
            "chain_data": chain_data if chain_data.get("ok") else {},
        }
        return render_template("result.html", result=result)

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(str(upload_dir), secure_filename(filename))

    @app.route("/verify", methods=["GET", "POST"])
    def verify():
        if request.method == "GET":
            return render_template("verify.html")

        image = request.files.get("image")
        valid, error = _validate_upload(image)
        if not valid:
            return render_template(
                "result.html",
                result=_failure(error, "Choose a supported image and try again."),
            ), 400

        original_name = secure_filename(image.filename)
        suffix = Path(original_name).suffix.lower()
        temp_path = None
        try:
            temp_file = tempfile.NamedTemporaryFile(
                prefix="aivb-verify-",
                suffix=suffix,
                dir=upload_dir,
                delete=False,
            )
            temp_path = Path(temp_file.name)
            with temp_file:
                shutil.copyfileobj(image.stream, temp_file)
            _validate_image(temp_path)
            result = agent.verify_image(str(temp_path))
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            result = _failure(
                f"Verification failed because the image could not be processed: {exc}",
                "Choose a readable PNG, JPG, or JPEG image.",
            )
        finally:
            if temp_path:
                temp_path.unlink(missing_ok=True)

        status_code = 503 if result["status"] == "Verification Failed" and (
            result.get("blockchain_status") == "Lookup failed"
        ) else 200
        return render_template("result.html", result=result), status_code

    @app.route("/system-status")
    def system_status():
        return render_template("system_status.html", health=service.health())

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
