from functools import lru_cache
from os import getenv

from dotenv import load_dotenv


load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.openai_base_url = getenv("OPENAI_BASE_URL", "https://api.openai.com").rstrip("/")
        self.openai_responses_path = getenv("OPENAI_RESPONSES_PATH", "/v1/responses")
        self.openai_model = getenv("OPENAI_MODEL", "gpt-5.5")
        self.openai_api_key = getenv("OPENAI_API_KEY", "")
        self.openai_timeout_seconds = float(getenv("OPENAI_TIMEOUT_SECONDS", "30"))
        self.openai_reasoning_effort = getenv("OPENAI_REASONING_EFFORT", "medium")
        self.openai_realtime_calls_path = getenv("OPENAI_REALTIME_CALLS_PATH", "/v1/realtime/calls")
        self.openai_realtime_model = getenv("OPENAI_REALTIME_MODEL", "gpt-realtime-2")
        self.openai_realtime_voice = getenv("OPENAI_REALTIME_VOICE", "coral")
        self.openai_web_search = getenv("OPENAI_WEB_SEARCH", "true").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        mock_default = "false" if self.openai_api_key else "true"
        mock_llm = getenv("MIITAN_MOCK_LLM", mock_default)
        self.mock_llm = mock_llm.lower() in {
            "1",
            "true",
            "yes",
            "on",
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
