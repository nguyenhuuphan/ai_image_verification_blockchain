# AI Image Verification Using Blockchain

This is a course prototype for registering and verifying images with:

- LSB image watermarking
- SHA-256 hashing
- a Solidity smart contract
- Ganache
- Flask and Web3.py

The image itself is stored outside the blockchain. The smart contract stores
only the image hash, watermark ID, creator address, timestamp, and registration
status.

## How it works

### Register an image

1. Upload a PNG, JPG, or JPEG image.
2. The application converts it to RGB.
3. A watermark ID is generated and embedded in the red-channel LSBs.
4. The watermarked image is saved as PNG.
5. Its SHA-256 hash and watermark ID are registered on Ganache.

### Verify an image

1. Upload an image.
2. The application extracts the watermark.
3. It calculates the image SHA-256 hash.
4. It checks the smart contract for a matching record.
5. It returns one of these results:

| Result | Meaning |
| --- | --- |
| Authentic | The watermark and blockchain record match. |
| Modified | A watermark exists, but the image hash is not registered. |
| Suspicious | The hash exists, but the watermark cannot be confirmed. |
| Unknown | No watermark or blockchain record was found. |
| Verification Failed | The image or blockchain connection could not be processed. |

## Setup

Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Install Ganache:

```powershell
npm install
```

Copy the environment example:

```powershell
Copy-Item backend/.env.example backend/.env
```

## Run

Start Ganache:

```powershell
npm run ganache
```

In another terminal, deploy the smart contract:

```powershell
python deploy_contract.py --update-env
```

Start the Flask application:

```powershell
python backend/app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Main files

```text
backend/app.py                         Flask application
backend/watermark.py                   LSB watermark embedding and extraction
backend/hash_utils.py                  SHA-256 hashing
backend/blockchain_service.py          Ganache and smart-contract connection
backend/ai_agent.py                    Verification decision rules
smart_contract/ImageVerification.sol   Solidity smart contract
deploy_contract.py                     Contract deployment script
frontend/                              Web pages and CSS
screenshots/report/                    Report screenshots
```
