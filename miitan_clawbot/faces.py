from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Face:
    id: str
    label: str
    image: str
    color: str


FACES = [
    Face("joy", "喜び", "maid_01_yorokobi_joy.png", "#ffd166"),
    Face("anger", "怒り", "maid_02_ikari_anger.png", "#ef476f"),
    Face("sadness", "悲しみ", "maid_03_kanashimi_sadness.png", "#5dade2"),
    Face("fun", "楽しみ", "maid_04_tanoshimi_fun.png", "#06d6a0"),
    Face("normal", "通常", "maid_05_tsujo_normal.png", "#f5b7c8"),
    Face("shy", "照れ", "maid_06_tere_shy.png", "#ff9fb2"),
    Face("surprise", "驚き", "maid_07_odoroki_surprise.png", "#a78bfa"),
    Face("troubled", "困り", "maid_08_komari_troubled.png", "#8ecae6"),
    Face("clumsy", "ドジっ子", "maid_09_dojikko_clumsy.png", "#adb5bd"),
]

DEFAULT_FACE = FACES[4]
FACE_BY_IMAGE = {face.image: face for face in FACES}
FACE_BY_LABEL = {face.label: face for face in FACES}
FACE_BY_LEGACY_EMOTION = {
    "happy": FACES[0],
    "angry": FACES[1],
    "sad": FACES[2],
    "fun": FACES[3],
    "normal": FACES[4],
    "shy": FACES[5],
    "surprised": FACES[6],
    "thinking": FACES[7],
    "sleepy": FACES[8],
}


def face_to_dict(face: Face) -> dict[str, str]:
    return {
        "id": face.id,
        "label": face.label,
        "image": face.image,
        "color": face.color,
    }


def normalize_image(filename: Any) -> str:
    if not isinstance(filename, str):
        return DEFAULT_FACE.image

    image = Path(filename).name
    if image in FACE_BY_IMAGE:
        return image

    return DEFAULT_FACE.image


def face_for_emotion(emotion: str | None) -> Face:
    if not emotion:
        return DEFAULT_FACE

    return FACE_BY_LABEL.get(emotion) or FACE_BY_LEGACY_EMOTION.get(emotion) or DEFAULT_FACE


def extract_face_json(text: str) -> tuple[str, dict[str, str] | None]:
    stripped = text.rstrip()
    for start in _candidate_json_starts(stripped):
        try:
            parsed = json.loads(stripped[start:])
        except json.JSONDecodeError:
            continue

        face_payload = _pick_face_payload(parsed)
        if face_payload is None:
            continue

        return stripped[:start].rstrip(), face_payload

    return text, None


def _candidate_json_starts(text: str) -> list[int]:
    starts = []
    for index, char in enumerate(text):
        if char in "[{":
            starts.append(index)
    return list(reversed(starts))


def _pick_face_payload(value: Any) -> dict[str, str] | None:
    if isinstance(value, dict):
        return _normalize_face_payload(value)

    if isinstance(value, list):
        for item in value:
            if normalized := _normalize_face_payload(item):
                return normalized

    return None


def _normalize_face_payload(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None

    if value.get("category") != "emotion":
        return None

    image = normalize_image(value.get("image"))
    face = FACE_BY_IMAGE.get(image, DEFAULT_FACE)
    emotion = value.get("emotion") if isinstance(value.get("emotion"), str) else face.label

    return {
        "category": "emotion",
        "emotion": emotion,
        "image": image,
    }
