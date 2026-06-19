# Report Screenshots

The completed report screenshots are stored in `screenshots/report/`.

| File | Description |
| --- | --- |
| `01-home-page.png` | Application home page |
| `02-ganache-running.png` | Ganache connection and contract status |
| `03-contract-deployment.png` | Smart-contract deployment |
| `04-register-page.png` | Image registration form |
| `05-registration-success.png` | Successful image registration |
| `06-ganache-transaction.png` | Blockchain transaction information |
| `07-watermarked-image.png` | Generated watermarked image |
| `08-verify-page.png` | Image verification form |
| `09-authentic-result.png` | Authentic result |
| `10-modified-result.png` | Modified result |
| `11-unknown-result.png` | Unknown result |
| `12-verification-failed.png` | Failed verification result |
| `13-evaluation-results.png` | Test-case result table |
| `14-automated-tests.png` | Test result evidence |

## Reproduce the result evidence

Start Ganache and run:

```powershell
npm run ganache
```

In another terminal:

```powershell
python verify_implementation.py
```

The script deploys a fresh smart contract, checks the watermark implementation,
and runs TC01-TC09 against real Ganache. The terminal result can be captured
again for the report without requiring mock blockchain data.
