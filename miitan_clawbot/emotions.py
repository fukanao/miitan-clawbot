from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Emotion:
    id: str
    label: str
    color: str


EMOTIONS = [
    Emotion("normal", "普通", "#f5b7c8"),
    Emotion("happy", "喜", "#ffd166"),
    Emotion("angry", "怒", "#ef476f"),
    Emotion("sad", "哀", "#5dade2"),
    Emotion("fun", "楽", "#06d6a0"),
    Emotion("surprised", "驚き", "#a78bfa"),
    Emotion("shy", "照れ", "#ff9fb2"),
    Emotion("thinking", "考え中", "#8ecae6"),
    Emotion("sleepy", "眠い", "#adb5bd"),
]

EMOTION_IDS = {emotion.id for emotion in EMOTIONS}

KEYWORDS = {
    "happy": ["嬉", "ありがとう", "最高", "好き", "やった", "助か", "よかった", "happy", "thanks"],
    "angry": ["怒", "むか", "嫌", "だめ", "最悪", "許せ", "angry"],
    "sad": ["悲", "寂", "つら", "泣", "困", "ごめん", "sad"],
    "fun": ["楽しい", "笑", "わくわく", "面白", "遊", "fun"],
    "surprised": ["驚", "びっくり", "まさか", "えっ", "すごい", "surprise"],
    "shy": ["照", "恥", "かわいい", "褒め", "shy"],
    "thinking": ["考", "どうしよう", "なぜ", "理由", "分析", "thinking"],
    "sleepy": ["眠", "疲", "おやすみ", "ねむ", "sleep"],
}


def normalize_emotion(value: str | None) -> str:
    if value in EMOTION_IDS:
        return value
    return "normal"


def infer_emotion(*texts: str) -> str:
    joined = " ".join(texts).lower()
    for emotion, keywords in KEYWORDS.items():
        if any(keyword.lower() in joined for keyword in keywords):
            return emotion
    return "normal"
