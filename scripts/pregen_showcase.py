#!/usr/bin/env python3
"""把六句固定台词合成 mp3。

两个人共用 Lex 的复刻音色。音色绑在 qwen-audio-3.1-tts-flash，
走非实时 HTTP 合成。音色 ID 从本机 .env 的 SHOWCASE_VOICE 读取。

    .venv/bin/python scripts/pregen_showcase.py --dry-run
    .venv/bin/python scripts/pregen_showcase.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from backend.showcase import SHOWCASE_TTS_MODEL, STORY, pregen_voice_id  # noqa: E402

SYNTH_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer"


def _load_dotenv() -> None:
    env_path = REPO / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def synth_mp3(text: str, *, voice: str, model: str, api_key: str) -> bytes:
    body = json.dumps(
        {
            "model": model,
            "input": {
                "text": text,
                "voice": voice,
                "format": "mp3",
                "sample_rate": 24000,
            },
        }
    ).encode()
    request = urllib.request.Request(
        SYNTH_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.loads(response.read().decode())
    audio_url = payload["output"]["audio"]["url"]
    with urllib.request.urlopen(audio_url, timeout=120) as response:
        audio = response.read()
    if len(audio) < 1000 or not audio.startswith(b"ID3"):
        raise RuntimeError(f"synthesis did not return an mp3 ({len(audio)} bytes)")
    return audio


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只打印六句和模型，不请求语音接口")
    args = parser.parse_args()
    _load_dotenv()

    model = os.getenv("SHOWCASE_TTS_MODEL", "").strip() or SHOWCASE_TTS_MODEL
    if args.dry_run:
        voice = os.getenv("SHOWCASE_VOICE", "").strip()
        print(f"voice_set={bool(voice)} model={model} turns={len(STORY)}")
        for turn in STORY:
            print(f"{turn.index} {turn.speaker} {turn.audio} chars={len(turn.text)}")
        return 0

    api_key = (os.getenv("DASHSCOPE_API_KEY") or "").strip()
    if not api_key:
        print("Missing DASHSCOPE_API_KEY", file=sys.stderr)
        return 2
    voice = pregen_voice_id()

    for turn in STORY:
        dest = REPO / "frontend" / "public" / turn.audio.lstrip("/")
        print(f"Synthesizing {dest.name} ...", flush=True)
        dest.write_bytes(synth_mp3(turn.text, voice=voice, model=model, api_key=api_key))
        print(f"Wrote {dest} ({dest.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130) from None
