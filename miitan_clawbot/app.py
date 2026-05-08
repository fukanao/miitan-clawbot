from __future__ import annotations

import json
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import get_settings
from .emotions import EMOTIONS
from .faces import FACES, face_to_dict
from .openai_client import LLMError, MIITAN_BASE_PROMPT, OpenAIClient


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_ROOT / "static"
MAID_FACES_DIR = PROJECT_ROOT / "maid_faces"

app = FastAPI(title="Miitan Clawbot")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/maid_faces", StaticFiles(directory=MAID_FACES_DIR), name="maid_faces")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    image: str | None = Field(default=None, max_length=3_000_000)
    previous_response_id: str | None = Field(default=None, max_length=200)


@app.get("/")
async def index() -> RedirectResponse:
    return RedirectResponse("/static/index.html")


@app.get("/api/emotions")
async def emotions() -> list[dict[str, str]]:
    return [emotion.__dict__ for emotion in EMOTIONS]


@app.get("/api/faces")
async def faces() -> list[dict[str, str]]:
    return [face_to_dict(face) for face in FACES]


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict[str, object]:
    settings = get_settings()
    client = OpenAIClient(settings)

    try:
        result = await client.chat(
            request.message,
            request.image,
            previous_response_id=request.previous_response_id,
        )
    except LLMError as exc:
        return {
            "reply": str(exc),
            "emotion": "困り",
            "image": "maid_08_komari_troubled.png",
            "response_id": request.previous_response_id or "",
            "citations": [],
        }

    return result


@app.post("/api/realtime/session")
async def realtime_session(request: Request) -> Response:
    settings = get_settings()
    if not settings.openai_api_key:
        return PlainTextResponse("OPENAI_API_KEY is not set.", status_code=500)

    offer_sdp = (await request.body()).decode("utf-8")
    session_config = {
        "type": "realtime",
        "model": settings.openai_realtime_model,
        "instructions": (
            f"{MIITAN_BASE_PROMPT}"
            "音声では、若々しく子供っぽい印象の高めの声で話してください。"
            "明るく元気で、少し甘えた雰囲気のかわいいメイドのように話してください。"
            "低い声、落ち着いた声、大人びた声にはしないでください。"
            "語尾はやわらかく、短めの文で、親しみやすく返してください。"
        ),
        "reasoning": {"effort": settings.openai_reasoning_effort},
        "output_modalities": ["audio"],
        "audio": {
            "input": {
                "turn_detection": {"type": "semantic_vad"},
            },
            "output": {
                "voice": settings.openai_realtime_voice,
            },
        },
    }

    try:
        async with httpx.AsyncClient(timeout=settings.openai_timeout_seconds) as client:
            response = await client.post(
                f"{settings.openai_base_url}{settings.openai_realtime_calls_path}",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                files={
                    "sdp": (None, offer_sdp, "application/sdp"),
                    "session": (None, json.dumps(session_config), "application/json"),
                },
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip()
        message = f"OpenAI Realtime APIへの接続に失敗しました: HTTP {exc.response.status_code}"
        if detail:
            message = f"{message} {detail}"
        return PlainTextResponse(message, status_code=502)
    except httpx.HTTPError as exc:
        detail = str(exc) or exc.__class__.__name__
        return PlainTextResponse(
            f"OpenAI Realtime APIへの接続に失敗しました: {detail}",
            status_code=502,
        )

    return Response(content=response.text, media_type="application/sdp")


@app.get("/api/realtime/token")
async def realtime_token() -> Response:
    settings = get_settings()
    if not settings.openai_api_key:
        return PlainTextResponse("OPENAI_API_KEY is not set.", status_code=500)

    session_config = {
        "session": {
            "type": "realtime",
            "model": settings.openai_realtime_model,
            "instructions": (
                f"{MIITAN_BASE_PROMPT}"
                "音声では、若々しく子供っぽい印象の高めの声で話してください。"
                "明るく元気で、少し甘えた雰囲気のかわいいメイドのように話してください。"
                "低い声、落ち着いた声、大人びた声にはしないでください。"
                "語尾はやわらかく、短めの文で、親しみやすく返してください。"
            ),
            "reasoning": {"effort": settings.openai_reasoning_effort},
            "output_modalities": ["audio"],
            "audio": {
                "input": {
                    "turn_detection": {"type": "semantic_vad"},
                },
                "output": {
                    "voice": settings.openai_realtime_voice,
                },
            },
        },
    }

    try:
        async with httpx.AsyncClient(timeout=settings.openai_timeout_seconds) as client:
            response = await client.post(
                f"{settings.openai_base_url}/v1/realtime/client_secrets",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=session_config,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return PlainTextResponse(
            _openai_error_message("OpenAI Realtime token", exc.response),
            status_code=502,
        )
    except httpx.HTTPError as exc:
        detail = str(exc) or exc.__class__.__name__
        return PlainTextResponse(
            f"OpenAI Realtime tokenへの接続に失敗しました: {detail}",
            status_code=502,
        )

    payload = response.json()
    payload["realtime_url"] = f"{settings.openai_base_url}{settings.openai_realtime_calls_path}"
    return Response(content=json.dumps(payload), media_type="application/json")


def _openai_error_message(label: str, response: httpx.Response) -> str:
    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type:
        return f"{label}への接続に失敗しました: HTTP {response.status_code}"

    detail = response.text.strip()
    message = f"{label}への接続に失敗しました: HTTP {response.status_code}"
    if detail:
        message = f"{message} {detail}"
    return message
