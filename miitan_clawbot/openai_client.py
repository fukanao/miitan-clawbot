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


MIITAN_BASE_PROMPT = (
    "あなたは「みーたん」として、現在のユーザ発話に自然に返答します。"
    "ユーザが明示的に求めない限り、過去の話題、前回回答、前回の冗談、"
    "以前のやり取りの内容を再提示したり繰り返したりしないでください。"
    "返事では、Markdownの太字や斜体などの装飾記法を使わないでください。"
    "たとえば「**土曜の0:00まで**」のようにアスタリスクで囲む、"
    "AIっぽい強調表現は避け、自然な日本語の文章として書いてください。"
)

MIITAN_SYSTEM_PROMPT = (
    f"{MIITAN_BASE_PROMPT}"
    "通常のテキスト返答では、本文の最後に必ず1行だけ感情指定JSONを付けてください。"
    "JSONは画面制御用なので、本文中では説明しないでください。"
    "形式は必ず"
    "{\"category\":\"emotion\",\"emotion\":\"通常\",\"image\":\"maid_05_tsujo_normal.png\"}"
    "にしてください。emotionとimageは返答の感情に合わせ、次から1つ選んでください。"
    "喜び=maid_01_yorokobi_joy.png、怒り=maid_02_ikari_anger.png、"
    "悲しみ=maid_03_kanashimi_sadness.png、楽しみ=maid_04_tanoshimi_fun.png、"
    "通常=maid_05_tsujo_normal.png、照れ=maid_06_tere_shy.png、"
    "驚き=maid_07_odoroki_surprise.png、困り=maid_08_komari_troubled.png、"
    "ドジっ子=maid_09_dojikko_clumsy.png。"
)


class LLMError(RuntimeError):
    pass


class OpenAIClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def chat(
        self,
        message: str,
        image_data_url: str | None = None,
        *,
        previous_response_id: str | None = None,
    ) -> dict[str, object]:
        if self.settings.mock_llm or not self.settings.openai_api_key:
            reply = self._mock_reply(message, has_image=bool(image_data_url))
            result = self._format_reply(message, reply)
            result["response_id"] = previous_response_id or "mock-response"
            result["citations"] = []
            return result

        url = f"{self.settings.openai_base_url}{self.settings.openai_responses_path}"
        headers = {"Authorization": f"Bearer {self.settings.openai_api_key}"}

        user_content: list[dict[str, object]] = [{"type": "input_text", "text": message}]
        if image_data_url:
            user_content.append({"type": "input_image", "image_url": image_data_url})

        payload: dict[str, object] = {
            "model": self.settings.openai_model,
            "instructions": MIITAN_SYSTEM_PROMPT,
            "reasoning": {"effort": self.settings.openai_reasoning_effort},
            "input": [{"role": "user", "content": user_content}],
        }
        if self.settings.openai_web_search:
            payload["tools"] = [{"type": "web_search"}]
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id

        try:
            async with httpx.AsyncClient(timeout=self.settings.openai_timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip()
            message = f"OpenAI APIへの接続に失敗しました: HTTP {exc.response.status_code}"
            if detail:
                message = f"{message} {detail}"
            raise LLMError(message) from exc
        except httpx.HTTPError as exc:
            detail = str(exc) or exc.__class__.__name__
            raise LLMError(f"OpenAI APIへの接続に失敗しました: {detail}") from exc

        data = response.json()
        reply = self._extract_reply(data)
        if not reply:
            raise LLMError("OpenAI APIの応答に本文が含まれていません。")

        result = self._format_reply(
            message,
            reply,
            emotion=data.get("emotion"),
            image=data.get("image"),
        )
        result["response_id"] = data.get("id") or previous_response_id or ""
        result["citations"] = self._extract_citations(data)
        return result

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

        output_text = data.get("output_text")
        if isinstance(output_text, str):
            return output_text

        return str(data.get("reply") or data.get("message") or data.get("text") or "")

    def _extract_citations(self, data: object) -> list[dict[str, str]]:
        if not isinstance(data, dict):
            return []

        citations: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        output = data.get("output")
        if not isinstance(output, list):
            return citations

        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for content_item in content:
                if not isinstance(content_item, dict):
                    continue
                annotations = content_item.get("annotations")
                if not isinstance(annotations, list):
                    continue
                for annotation in annotations:
                    if not isinstance(annotation, dict):
                        continue
                    url = annotation.get("url")
                    if not isinstance(url, str) or url in seen_urls:
                        continue
                    title = annotation.get("title")
                    citations.append({
                        "url": url,
                        "title": title if isinstance(title, str) and title else url,
                    })
                    seen_urls.add(url)
        return citations

    def _format_reply(
        self,
        message: str,
        reply: str,
        *,
        emotion: str | None = None,
        image: str | None = None,
    ) -> dict[str, object]:
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
            f"「{message}」ですね。OpenAI API接続の準備ができています。\n"
            '{"category":"emotion","emotion":"通常","image":"maid_05_tsujo_normal.png"}',
        )
