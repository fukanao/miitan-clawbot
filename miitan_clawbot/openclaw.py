from __future__ import annotations

import httpx

from .config import Settings
from .emotions import infer_emotion, normalize_emotion
from .faces import (
    DEFAULT_FACE,
    extract_face_json,
    face_for_emotion,
    normalize_image,
)


class OpenClawError(RuntimeError):
    pass


class OpenClawClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def chat(self, message: str, history: list[dict[str, str]]) -> dict[str, str]:
        if self.settings.mock_openclaw or not self.settings.openclaw_base_url:
            reply = self._mock_reply(message)
            return self._format_reply(message, reply)

        url = f"{self.settings.openclaw_base_url}{self.settings.openclaw_chat_path}"
        headers = {}
        if self.settings.openclaw_api_key:
            headers["Authorization"] = f"Bearer {self.settings.openclaw_api_key}"

        payload = {
            "message": message,
            "history": history,
        }

        try:
            async with httpx.AsyncClient(timeout=self.settings.openclaw_timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OpenClawError(f"OpenClawへの接続に失敗しました: {exc}") from exc

        data = response.json()
        reply = str(data.get("reply") or data.get("message") or data.get("text") or "")
        if not reply:
            raise OpenClawError("OpenClawの応答に reply/message/text が含まれていません。")

        return self._format_reply(
            message,
            reply,
            emotion=data.get("emotion"),
            image=data.get("image"),
        )

    def _format_reply(
        self,
        message: str,
        reply: str,
        *,
        emotion: str | None = None,
        image: str | None = None,
    ) -> dict[str, str]:
        clean_reply, face_json = extract_face_json(reply)

        if face_json:
            return {
                "reply": clean_reply,
                "emotion": face_json["emotion"],
                "image": face_json["image"],
            }

        if image:
            normalized_image = normalize_image(image)
            return {
                "reply": clean_reply,
                "emotion": emotion or face_for_emotion(None).label,
                "image": normalized_image,
            }

        legacy_emotion = normalize_emotion(emotion) if emotion else infer_emotion(message, clean_reply)
        face = face_for_emotion(legacy_emotion)
        return {
            "reply": clean_reply,
            "emotion": face.label,
            "image": face.image or DEFAULT_FACE.image,
        }

    def _mock_reply(self, message: str) -> str:
        emotion = infer_emotion(message)
        replies = {
            "happy": (
                "うれしいです。私も楽しくなってきました。\n"
                '{"category":"emotion","emotion":"喜び","image":"maid_01_yorokobi_joy.png"}'
            ),
            "angry": (
                "落ち着いて、一緒に原因を見つけましょう。\n"
                '{"category":"emotion","emotion":"怒り","image":"maid_02_ikari_anger.png"}'
            ),
            "sad": (
                "それはつらかったですね。そばにいます。\n"
                '{"category":"emotion","emotion":"悲しみ","image":"maid_03_kanashimi_sadness.png"}'
            ),
            "fun": (
                "楽しそうです。もっと聞かせてください。\n"
                '{"category":"emotion","emotion":"楽しみ","image":"maid_04_tanoshimi_fun.png"}'
            ),
            "surprised": (
                "びっくりしました。詳しく教えてください。\n"
                '{"category":"emotion","emotion":"驚き","image":"maid_07_odoroki_surprise.png"}'
            ),
            "shy": (
                "えへへ、少し照れます。\n"
                '{"category":"emotion","emotion":"照れ","image":"maid_06_tere_shy.png"}'
            ),
            "thinking": (
                "少し考えますね。順番に整理してみます。\n"
                '{"category":"emotion","emotion":"困り","image":"maid_08_komari_troubled.png"}'
            ),
            "sleepy": (
                "眠そうですね。無理しないでください。\n"
                '{"category":"emotion","emotion":"ドジっ子","image":"maid_09_dojikko_clumsy.png"}'
            ),
        }
        return replies.get(
            emotion,
            f"「{message}」ですね。OpenClaw接続の準備ができています。\n"
            '{"category":"emotion","emotion":"通常","image":"maid_05_tsujo_normal.png"}',
        )
