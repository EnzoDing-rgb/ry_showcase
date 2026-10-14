#!/usr/bin/env python3
"""把六句固定台词合成 mp3。两个人都用 VOICE_ID_LEX。

会消耗 DashScope 额度。没充值时只跑 --dry-run，不要去掉该参数。

    .venv/bin/python scripts/pregen_showcase.py --dry-run
    .venv/bin/python scripts/pregen_showcase.py
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from backend.showcase import STORY, pregen_voice_id  # noqa: E402
from scripts.pregen_lex_opening import pcm_to_mp3, synth_pcm  # noqa: E402
from backend.tts_manager import TTS_MODEL, TTS_WS_URL  # noqa: E402


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只打印六句和声线，不请求语音接口")
    args = parser.parse_args()
    _load_dotenv()

    voice = pregen_voice_id()
    if args.dry_run:
        print(f"voice={'set' if voice else 'MISSING VOICE_ID_LEX'} turns={len(STORY)}")
        for turn in STORY:
            print(f"{turn.index} {turn.speaker} {turn.audio} chars={len(turn.text)}")
        return 0

    api_key = (os.getenv("DASHSCOPE_API_KEY") or "").strip()
    model = (os.getenv("TTS_MODEL") or "").strip() or TTS_MODEL
    ws_url = (os.getenv("TTS_WS_URL") or "").strip() or TTS_WS_URL
    if not api_key:
        print("Missing DASHSCOPE_API_KEY", file=sys.stderr)
        return 2
    if not voice:
        print("Missing VOICE_ID_LEX", file=sys.stderr)
        return 2

    for turn in STORY:
        dest = REPO / "frontend" / "public" / turn.audio.lstrip("/")
        print(f"Synthesizing {dest.name} ...", flush=True)
        pcm = synth_pcm(turn.text, voice=voice, model=model, ws_url=ws_url, api_key=api_key)
        if len(pcm) < 1000:
            raise SystemExit(f"{dest.name} PCM too small ({len(pcm)} bytes)")
        pcm_to_mp3(pcm, dest)
        print(f"Wrote {dest} ({dest.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130) from None
