from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_key: str
    secret_key: str
    app_id: str
    redirect_uri: str
    server: str

    sg_plant_name: str
    sh_plant_name: str

    cache_ttl_seconds: int
    token_file: str = "tokens.json"


def get_settings() -> Settings:
    def req(name: str) -> str:
        v = os.getenv(name)
        if not v:
            raise RuntimeError(f"Missing required env var: {name}")
        return v

    return Settings(
        app_key=req("SUNgrow_APP_KEY"),
        secret_key=req("SUNgrow_SECRET_KEY"),
        app_id=req("SUNgrow_APP_ID"),
        redirect_uri=req("SUNgrow_REDIRECT_URI"),
        server=os.getenv("SUNgrow_SERVER", "Europe"),
        sg_plant_name=req("SG_PLANT_NAME"),
        sh_plant_name=req("SH_PLANT_NAME"),
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "90")),
    )
