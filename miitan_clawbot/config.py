from functools import lru_cache
from os import getenv

from dotenv import load_dotenv


load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.openclaw_base_url = getenv("OPENCLAW_BASE_URL", "").rstrip("/")
        self.openclaw_chat_path = getenv("OPENCLAW_CHAT_PATH", "/v1/chat/completions")
        self.openclaw_model = getenv("OPENCLAW_MODEL", "openclaw/default")
        self.openclaw_user = getenv("OPENCLAW_USER", "web-ui-user")
        self.openclaw_api_key = getenv("OPENCLAW_API_KEY", "")
        self.openclaw_timeout_seconds = float(getenv("OPENCLAW_TIMEOUT_SECONDS", "30"))
        self.mock_openclaw = getenv("MIITAN_MOCK_OPENCLAW", "true").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
