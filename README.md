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

====
To install to Home Assistant and integrate with Loxone : 

Sungrow Bridge (Home Assistant Add-on) — Clean Reinstall Guide
0) Prereqs

Home Assistant OS installed and running

You know your HA IP (example: 192.168.68.54)

You have your Sungrow developer credentials:

app_key

secret_key

app_id

redirect URI must match exactly what you configure in Sungrow portal

Repo:

https://github.com/bramvg87/sungrow-bridge

1) Install required HA add-ons

In Home Assistant:

Settings → Add-ons
Install:

Studio Code Server (recommended)

(optional) Terminal & SSH (useful)

Start Studio Code Server.

2) Create the local add-ons folder (host side)

Open Terminal & SSH and run:

mkdir -p /addons/local

3) Clone the repo into the correct location

Clone directly into the add-ons folder (this is the important part):

cd /addons/local
git clone https://github.com/bramvg87/sungrow-bridge.git sungrow-bridge


You should now have:

/addons/local/sungrow-bridge

4) Make it editable in VS Code (recommended)

Studio Code Server can always edit /config easily, so create a symlink:

ln -s /addons/local/sungrow-bridge /config/sungrow-bridge


Now you can edit here in VS Code:

/config/sungrow-bridge (this is a symlink)

And Supervisor will load the add-on from:

/addons/local/sungrow-bridge

Verify:

ls -la /config/sungrow-bridge
ls -la /addons/local/sungrow-bridge

5) Reload the Add-on Store

Home Assistant:

Settings → Add-ons → Add-on Store

top right ⋮ → Reload

Scroll down → Local add-ons
You should see Sungrow Bridge.

6) Install the add-on

Click Sungrow Bridge → Install.

(Wait until install finishes.)

7) Configure the add-on

Open the add-on Configuration tab and fill in:

port: 8088

sungrow_app_key: ...

sungrow_secret_key: ...

sungrow_app_id: ...

sungrow_redirect_uri: http://<HA_IP>:8088/auth/callback

sungrow_server: Europe

sg_plant_name: exact Sungrow plant name for SG inverter

sh_plant_name: exact Sungrow plant name for SH inverter

cache_ttl_seconds: 90 (recommended)

Save.

✅ Make sure the redirect URI matches exactly what you entered in the Sungrow developer portal.

8) Start the add-on + authenticate once

Start the add-on.

Test health:

http://<HA_IP>:8088/health

Then authenticate:

Open http://<HA_IP>:8088/auth/start

Copy the authorize_url into a browser

Complete Sungrow OAuth

You should land on /auth/callback?... and get OK

9) Test the Loxone endpoint

Test in browser:

http://<HA_IP>:8088/realtime/loxone

You should get a flat JSON payload like:

sg_power_w

sh_power_w

sh_load_power_w

sh_battery_soc_pct

etc.

✅ This endpoint supports GET, which is what Loxone Virtual HTTP Input needs.

10) Persistence verification (recommended)

To confirm tokens survive reboot:

Restart Home Assistant (Settings → System → Restart)

After reboot, open:

http://<HA_IP>:8088/realtime/loxone

If it works without re-auth → persistence is working.

(Add-on stores tokens/cache under its persistent /data volume automatically.)

Loxone Setup (minimal)

Use Virtual HTTP Input (GET):

URL: http://<HA_IP>:8088/realtime/loxone

Poll interval: 60s (recommended; your cache is 90s)

Parse the JSON keys you want into analog values.

Updating later (from git)

If you want to update the add-on to latest GitHub version:

cd /addons/local/sungrow-bridge
git pull


Then in HA add-on page:

Rebuild (or uninstall/install if needed)

Restart