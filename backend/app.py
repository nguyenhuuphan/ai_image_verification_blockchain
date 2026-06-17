from flask import Flask, render_template, request
from pathlib import Path
from watermark import embed_watermark
from hash_utils import generate_sha256_hash
from blockchain_service import BlockchainService
from ai_agent import ImageVerificationAgent

app = Flask(__name__, template_folder='../frontend')
UPLOAD_DIR = Path('uploads')
UPLOAD_DIR.mkdir(exist_ok=True)

blockchain_service = BlockchainService()
agent = ImageVerificationAgent(blockchain_service)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    image = request.files['image']
    watermark_id = request.form.get('watermark_id', 'WMK-2026-001')
    input_path = UPLOAD_DIR / image.filename
    output_path = UPLOAD_DIR / f'watermarked_{image.filename}'
    image.save(input_path)

    embed_watermark(str(input_path), str(output_path), watermark_id)
    image_hash = generate_sha256_hash(str(output_path))
    result = blockchain_service.register_image(image_hash, watermark_id)
    return render_template('result.html', result=result)

@app.route('/verify', methods=['POST'])
def verify():
    image = request.files['image']
    input_path = UPLOAD_DIR / image.filename
    image.save(input_path)
    result = agent.verify_image(str(input_path))
    return render_template('result.html', result=result)

if __name__ == '__main__':
    app.run(debug=True)
