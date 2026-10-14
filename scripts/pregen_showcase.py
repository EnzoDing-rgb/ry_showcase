#!/usr/bin/env python3
"""把六句固定台词合成 mp3。

这个账号能调通的是 qwen3-tts-flash-realtime。Lex 的复刻音色绑在
qwen3-tts-vc-realtime-2026-01-15 上，当前密钥调用该模型会返回 Model not exist，
所以两人都先用系统音色 Cherry（芊悦，普通话）。

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

from backend.showcase import SHOWCASE_TTS_MODEL, SHOWCASE_VOICE, STORY  # noqa: E402
from scripts.pregen_lex_opening import pcm_to_mp3, synth_pcm  # noqa: E402
from backend.tts_manager import TTS_WS_URL  # noqa: E402


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

    voice = os.getenv("SHOWCASE_VOICE", "").strip() or SHOWCASE_VOICE
    model = os.getenv("SHOWCASE_TTS_MODEL", "").strip() or SHOWCASE_TTS_MODEL
    if args.dry_run:
        print(f"voice={voice} model={model} turns={len(STORY)}")
        for turn in STORY:
            print(f"{turn.index} {turn.speaker} {turn.audio} chars={len(turn.text)}")
        return 0

    api_key = (os.getenv("DASHSCOPE_API_KEY") or "").strip()
    ws_url = (os.getenv("TTS_WS_URL") or "").strip() or TTS_WS_URL
    if not api_key:
        print("Missing DASHSCOPE_API_KEY", file=sys.stderr)
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
