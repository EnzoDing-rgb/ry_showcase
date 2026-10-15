#!/usr/bin/env python3
"""把六句固定台词合成 mp3。

两个人共用 Lex 的复刻音色。音色绑在 qwen-audio-3.1-tts-flash，
走非实时 HTTP 合成。音色 ID 从本机 .env 的 SHOWCASE_VOICE 读取。

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

from backend.showcase import SHOWCASE_TTS_MODEL, STORY, synthesize_reply  # noqa: E402


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

    if not (os.getenv("DASHSCOPE_API_KEY") or "").strip():
        print("Missing DASHSCOPE_API_KEY", file=sys.stderr)
        return 2

    for turn in STORY:
        dest = REPO / "frontend" / "public" / turn.audio.lstrip("/")
        print(f"Synthesizing {dest.name} ...", flush=True)
        dest.write_bytes(synthesize_reply(turn.text))
        print(f"Wrote {dest} ({dest.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130) from None
