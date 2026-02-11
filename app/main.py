from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import get_settings
from .sungrow_service import SungrowService

settings = get_settings()
svc = SungrowService(settings)

app = FastAPI(title="Sungrow Bridge", version="0.2.0")


class EmptyPost(BaseModel):
    pass


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/auth/start")
def auth_start():
    """
    Open the returned URL in your browser, approve access,
    and you'll be redirected to /auth/callback with ?code=...
    """
    return {"authorize_url": svc.auth_url()}


@app.get("/auth/callback")
async def auth_callback(code: str):
    try:
        await svc.authorize_with_code(code)
        return {"ok": True, "message": "Authorized. You can now call POST /realtime"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/realtime")
async def realtime(_: EmptyPost | None = None):
    """
    Returns realtime data for BOTH plants (SG + SH) using a single Sungrow API call,
    cached for CACHE_TTL_SECONDS.
    """
    try:
        return await svc.get_realtime_all()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"{e}. If this is first run, visit GET /auth/start and complete OAuth.",
        )


@app.post("/sg/realtime")
async def sg_realtime(_: EmptyPost | None = None):
    """
    Returns realtime data for the SG5.0RS (Poolhouse) from the shared cached /realtime call.
    """
    try:
        data = await svc.get_realtime_all()
        return data["plants"]["sg"]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"{e}. If this is first run, visit GET /auth/start and complete OAuth.",
        )


@app.post("/sh/realtime")
async def sh_realtime(_: EmptyPost | None = None):
    """
    Returns realtime data for the SH5.0RS (Attic) from the shared cached /realtime call.
    """
    try:
        data = await svc.get_realtime_all()
        return data["plants"]["sh"]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"{e}. If this is first run, visit GET /auth/start and complete OAuth.",
        )

@app.post("/realtime/loxone")
async def realtime_loxone(_: EmptyPost | None = None):
    """
    Flat numeric JSON for Loxone (ASCII-only keys, no nested raw fields).
    """
    try:
        data = await svc.get_realtime_all()
        sg = data["plants"]["sg"]
        sh = data["plants"]["sh"]

        # pull a few extra SH fields from raw if present
        sh_raw = sh.get("raw", {})

        def raw_val(raw: dict, key: str):
            m = raw.get(key)
            return None if not m else m.get("value")

        out = {
            "ts": data.get("timestamp_unix"),

            "sg_power_w": sg.get("power_w"),
            "sg_daily_yield_wh": sg.get("daily_yield_wh"),
            "sg_total_yield_wh": sg.get("total_yield_wh"),
            "sg_inverter_ac_power_w": sg.get("inverter_ac_power_w"),

            "sh_power_w": sh.get("power_w"),
            "sh_daily_yield_wh": sh.get("daily_yield_wh"),
            "sh_total_yield_wh": sh.get("total_yield_wh"),

            # useful for hybrid inverter / future battery use:
            "sh_load_power_w": raw_val(sh_raw, "load_power"),
            "sh_battery_soc_pct": raw_val(sh_raw, "battery_level_soc") or raw_val(sh_raw, "energy_storage_soc_ems"),
        }

        # remove None values
        return {k: v for k, v in out.items() if v is not None}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"{e}. If this is first run, visit GET /auth/start and complete OAuth.",
        )
