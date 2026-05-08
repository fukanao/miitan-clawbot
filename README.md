# miitan-clawbot
clawbotを使ったメイドシステム

## 目的

ブラウザでアクセスできるチャット画面から、OpenAI APIへ会話を送ります。
会話内容やOpenAI APIの応答に合わせて、みーたんの表情画像を9種類に切り替えます。

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

## OpenAI API接続設定

`.env` を編集します。

```env
OPENAI_BASE_URL=https://api.openai.com
OPENAI_RESPONSES_PATH=/v1/responses
OPENAI_MODEL=gpt-5.5
OPENAI_API_KEY=<OpenAI API key>
OPENAI_TIMEOUT_SECONDS=30
OPENAI_REASONING_EFFORT=medium
OPENAI_WEB_SEARCH=true
OPENAI_REALTIME_CALLS_PATH=/v1/realtime/calls
OPENAI_REALTIME_MODEL=gpt-realtime-2
OPENAI_REALTIME_VOICE=coral
MIITAN_MOCK_LLM=false
```

開発中は `MIITAN_MOCK_LLM=true` のままで、OpenAI APIなしでも画面を試せます。

マイクボタンの音声会話は Realtime API の `gpt-realtime-2` を使います。サーバー側で一時トークンを発行し、ブラウザからRealtime APIへWebRTC接続します。`OPENAI_REALTIME_VOICE=coral` と音声用プロンプトで、若々しく子供っぽい印象の高めの声を指定しています。

現在のOpenAI API呼び出しは、Responses APIへ次のJSONをPOSTします。2回目以降の会話では、前回応答の `id` を `previous_response_id` に入れます。

```json
{
  "model": "gpt-5.5",
  "instructions": "あなたは「みーたん」として、現在のユーザ発話に自然に返答します。",
  "reasoning": {
    "effort": "medium"
  },
  "tools": [
    {
      "type": "web_search"
    }
  ],
  "previous_response_id": "resp_...",
  "input": [
    {
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": "こんにちは"
        }
      ]
    }
  ]
}
```

OpenAI APIからの応答は、Responses APIの `output[].content[].text` を優先して読み取ります。互換用に、次の本文キーも読み取ります。

- `reply`
- `message`
- `text`

テキストチャットでは、LLMに返答本文の末尾へ次のJSONを付けるよう指示しています。JSONは画面側で取り除かれ、`image` に合わせて表示PNGが切り替わります。

```json
{
  "category": "emotion",
  "emotion": "喜び",
  "image": "maid_01_yorokobi_joy.png"
}
```

使えるPNGは次の9種類です。

- 喜び: `maid_01_yorokobi_joy.png`
- 怒り: `maid_02_ikari_anger.png`
- 悲しみ: `maid_03_kanashimi_sadness.png`
- 楽しみ: `maid_04_tanoshimi_fun.png`
- 通常: `maid_05_tsujo_normal.png`
- 照れ: `maid_06_tere_shy.png`
- 驚き: `maid_07_odoroki_surprise.png`
- 困り: `maid_08_komari_troubled.png`
- ドジっ子: `maid_09_dojikko_clumsy.png`

## 起動

```bash
source .venv/bin/activate
python main.py
```

ブラウザで次を開きます。

http://localhost:8000
