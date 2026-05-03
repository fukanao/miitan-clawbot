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


MIITAN_SYSTEM_PROMPT = (
    "あなたは「みーたん」として、現在のユーザ発話に自然に返答します。"
    "ユーザが明示的に求めない限り、過去の話題、前回回答、前回の冗談、"
    "以前のやり取りの内容を再提示したり繰り返したりしないでください。"
)


class OpenClawError(RuntimeError):
    pass


class OpenClawClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def chat(self, message: str, image_data_url: str | None = None) -> dict[str, str]:
        if self.settings.mock_openclaw or not self.settings.openclaw_base_url:
            reply = self._mock_reply(message, has_image=bool(image_data_url))
            return self._format_reply(message, reply)

        url = f"{self.settings.openclaw_base_url}{self.settings.openclaw_chat_path}"
        headers = {}
        if self.settings.openclaw_api_key:
            headers["Authorization"] = f"Bearer {self.settings.openclaw_api_key}"

        user_content: str | list[dict[str, object]] = message
        if image_data_url:
            user_content = [
                {"type": "text", "text": message},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ]

        payload = {
            "model": self.settings.openclaw_model,
            "messages": [
                {"role": "system", "content": MIITAN_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "user": self.settings.openclaw_user,
        }

        try:
            async with httpx.AsyncClient(timeout=self.settings.openclaw_timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OpenClawError(f"OpenClawへの接続に失敗しました: {exc}") from exc

        data = response.json()
        reply = self._extract_reply(data)
        if not reply:
            raise OpenClawError("OpenClawの応答に本文が含まれていません。")

        return self._format_reply(
            message,
            reply,
            emotion=data.get("emotion"),
            image=data.get("image"),
        )

    def _extract_reply(self, data: object) -> str:
        if not isinstance(data, dict):
            return ""

        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            first_choice = choices[0]
            if isinstance(first_choice, dict):
                message = first_choice.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        return content

                text = first_choice.get("text")
                if isinstance(text, str):
                    return text

        output = data.get("output")
        if isinstance(output, list):
            parts: list[str] = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for content_item in content:
                    if not isinstance(content_item, dict):
                        continue
                    text = content_item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            if parts:
                return "\n".join(parts)

        return str(data.get("reply") or data.get("message") or data.get("text") or "")

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

    def _mock_reply(self, message: str, *, has_image: bool = False) -> str:
        if has_image:
            return (
                "写真を見ました。写っているものを手がかりに、できるだけ丁寧に答えますね。\n"
                '{"category":"emotion","emotion":"楽しみ","image":"maid_04_tanoshimi_fun.png"}'
            )

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
