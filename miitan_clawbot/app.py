from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import get_settings
from .emotions import EMOTIONS
from .faces import FACES, face_to_dict
from .openclaw import OpenClawClient, OpenClawError


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_ROOT / "static"
MAID_FACES_DIR = PROJECT_ROOT / "maid_faces"

app = FastAPI(title="Miitan Clawbot")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/maid_faces", StaticFiles(directory=MAID_FACES_DIR), name="maid_faces")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/emotions")
async def emotions() -> list[dict[str, str]]:
    return [emotion.__dict__ for emotion in EMOTIONS]


@app.get("/api/faces")
async def faces() -> list[dict[str, str]]:
    return [face_to_dict(face) for face in FACES]


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict[str, str]:
    settings = get_settings()
    client = OpenClawClient(settings)
    history = [message.model_dump() for message in request.history]

    try:
        result = await client.chat(request.message, history)
    except OpenClawError as exc:
        return {
            "reply": str(exc),
            "emotion": "困り",
            "image": "maid_08_komari_troubled.png",
        }

    return result
