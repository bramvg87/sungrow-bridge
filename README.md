# Sungrow Bridge (iSolarCloud → JSON for Loxone)

Minimal FastAPI service that authenticates to Sungrow iSolarCloud (OAuth2) using `pysolarcloud`,
then serves inverter/plant realtime info via HTTP POST endpoints.

## Setup (laptop)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# edit .env with your Sungrow values


## Testing
##run
uvicorn app.main:app --reload --port 8088

##then open
http://127.0.0.1:8088/health
http://127.0.0.1:8088/auth/start
After approval you'll land on /auth/callback
Copy the authorize_url into your browser and approve
After redirect success, test your JSON endpoint:



Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8088/realtime" -ContentType "application/json" -Body "{}"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8088/sg/realtime" -ContentType "application/json" -Body "{}"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8088/sh/realtime" -ContentType "application/json" -Body "{}"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8088/realtime" -ContentType "application/json" -Body "{}" |
  ConvertTo-Json -Depth 20
$r = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8088/realtime" -ContentType "application/json" -Body "{}"
$r.plants.sg
$r.plants.sh
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8088/realtime/loxone" -ContentType "application/json" -Body "{}"


## Prepare Raspberry Pi deployment
Two key changes before moving to the Pi:
A. Remove --reload on the Pi (production mode)
B. Persist OAuth tokens (so reboot doesn’t require manual login)
Right now, after a Pi reboot, you’ll likely need to reauthorize once. We should fix that next by storing auth state to disk.

