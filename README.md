# miitan-clawbot
clawbotを使ったメイドシステム

## 目的

ブラウザでアクセスできるチャット画面から、別ホストで動作しているOpenClawへ会話を送ります。
会話内容やOpenClawの応答に合わせて、みーたんの表情画像を9種類に切り替えます。

将来的な音声入力に向けて、ブラウザの音声入力の入口も用意しています。返答の音声読み上げは行いません。

## 表情

- `normal`: 普通
- `happy`: 喜
- `angry`: 怒
- `sad`: 哀
- `fun`: 楽
- `surprised`: 驚き
- `shy`: 照れ
- `thinking`: 考え中
- `sleepy`: 眠い

画像は `maid_faces/*.png` にあります。LLMの回答末尾に付加されたJSONの `image` に書かれたファイル名を表示します。

例:

```json
{
  "category": "emotion",
  "emotion": "喜び",
  "image": "maid_01_yorokobi_joy.png"
}
```

このJSONはチャット本文からは取り除かれ、画面には通常の返答文だけが表示されます。

## セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## OpenClaw接続設定

`.env` を編集します。

```env
OPENCLAW_BASE_URL=http://192.168.0.175:18789
OPENCLAW_CHAT_PATH=/v1/chat/completions
OPENCLAW_MODEL=openclaw/default
OPENCLAW_USER=web-ui-user
OPENCLAW_API_KEY=<OpenClaw Gatewayのtoken>
OPENCLAW_TIMEOUT_SECONDS=30
MIITAN_MOCK_OPENCLAW=false
```

開発中は `MIITAN_MOCK_OPENCLAW=true` のままで、OpenClawなしでも画面を試せます。

現在のOpenClaw呼び出しは、次のJSONをPOSTします。

```json
{
  "model": "openclaw/default",
  "messages": [
    {
      "role": "user",
      "content": "こんにちは"
    }
  ],
  "user": "web-ui-user"
}
```

OpenClawからの応答は、OpenAI互換の `choices[0].message.content` を優先して読み取ります。互換用に、次の本文キーも読み取ります。

- `reply`
- `message`
- `text`

表情をOpenClaw側で指定する場合は、応答に `emotion` を含めてください。

```json
{
  "reply": "こんにちは。今日もよろしくお願いします。",
  "emotion": "happy"
}
```

## 起動

```bash
source .venv/bin/activate
python main.py
```

ブラウザで次を開きます。

http://localhost:8000
