# miitan-clawbot
clawbotを使ったメイドシステム

## 目的

ブラウザでアクセスできるチャット画面から、別ホストで動作しているOpenClawへ会話を送ります。
会話内容やOpenClawの応答に合わせて、みーたんの表情画像を9種類に切り替えます。

将来的な音声会話に向けて、ブラウザの音声入力と音声読み上げの入口も用意しています。

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
OPENCLAW_BASE_URL=http://openclaw-host:8000
OPENCLAW_CHAT_PATH=/chat
OPENCLAW_API_KEY=
OPENCLAW_TIMEOUT_SECONDS=30
MIITAN_MOCK_OPENCLAW=false
```

開発中は `MIITAN_MOCK_OPENCLAW=true` のままで、OpenClawなしでも画面を試せます。

現在のOpenClaw呼び出しは、次のJSONをPOSTします。

```json
{
  "message": "こんにちは",
  "history": [
    { "role": "user", "content": "こんにちは" }
  ]
}
```

OpenClawからの応答は、次のどれかの本文キーを読み取ります。

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
