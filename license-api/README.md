# Valido License API

Serverless API for secure license validation and version checking.

## Endpoints

- `GET /api/validate?license_key=XXX&device_id=YYY` - Validate license and register device
- `GET /api/version` - Get latest app version info

## Deploy to Vercel

1. Install Vercel CLI:
```bash
npm install -g vercel
```

2. Deploy:
```bash
cd license-api
vercel
```

3. Set environment variables in Vercel dashboard:
```
DB_USER=postgres.touhjzfmgznpgljocrvg
DB_PASSWORD=Dwayne43$#@!
DB_HOST=aws-1-eu-west-2.pooler.supabase.com
DB_PORT=6543
DB_NAME=postgres
```

## Usage in Desktop App

```python
import requests

# Validate license
response = requests.get(
    "https://your-app.vercel.app/api/validate",
    params={
        "license_key": "ABC123",
        "device_id": "unique-device-id"
    }
)
data = response.json()
if data["valid"]:
    print("License is valid!")
```
