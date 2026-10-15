"""如意 SDK 现场演示：固定六句故事，提问走 DeepSeek，失败时不向外泄露密钥。"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

FACTS_PATH = Path(__file__).resolve().parents[1] / "docs" / "showcase" / "ruyi-facts.md"

QA_PAUSED_REPLY = (
    "这个问题我这次没答上来。"
    "可以先看已经讲过的三步：ruyi 装工具链和模拟器，ruyi venv 里编译并在模拟器跑通，"
    "再用 ruyi device provision 按板子装系统。Milk-V Duo、VisionFive、荔枝派、BPI-F3、"
    "DC-ROMA、HiFive 都走同一套入口，具体镜像以支持矩阵为准。"
)

_CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"


@dataclass(frozen=True)
class StoryTurn:
    index: int
    speaker: str
    text: str

    @property
    def audio(self) -> str:
        return f"/audio/ruyi-{self.index:02d}.mp3"

    def as_dict(self) -> dict[str, str | int]:
        return {
            "index": self.index,
            "speaker": self.speaker,
            "text": self.text,
            "audio": self.audio,
        }


STORY: tuple[StoryTurn, ...] = (
    StoryTurn(
        1,
        "developer",
        "我手头可能是 Milk-V Duo，也可能是 VisionFive 2、荔枝派 4A，或者 Banana Pi BPI-F3。"
        "每块板的文档各写各的，工具链、模拟器和系统镜像根本不知道从哪下手。",
    ),
    StoryTurn(
        2,
        "guide",
        "如意 SDK 就是把这些收成一个入口。先用 ruyi 装上工具链和模拟器，这套工具不绑死在某一块板上。",
    ),
    StoryTurn(
        3,
        "developer",
        "装好了，可路径又长又记不住。我要是换成 DC-ROMA 或者 HiFive，环境是不是得推倒重来？",
    ),
    StoryTurn(
        4,
        "guide",
        "不用。用 ruyi venv 建一个虚拟环境，把工具链和模拟器放进去。"
        "激活之后直接编译，先在模拟器里把程序跑通。换板子，这套环境还在。",
    ),
    StoryTurn(
        5,
        "developer",
        "模拟器过了。真机呢？Duo、VisionFive、荔枝派、BPI-F3，镜像都不一样。",
    ),
    StoryTurn(
        6,
        "guide",
        "用 ruyi device provision。它按开发板列出能装的系统镜像，再带你装到对应的板上。"
        "支持矩阵里还有更多板子。现场有问题，可以直接问我。",
    ),
)


def load_facts() -> str:
    return FACTS_PATH.read_text(encoding="utf-8")


def story_payload() -> dict:
    return {
        "title": "如意 SDK",
        "subtitle": "同一套工具，许多块 RISC-V 开发板",
        "turns": [turn.as_dict() for turn in STORY],
    }


SHOWCASE_TTS_MODEL = "qwen-audio-3.1-tts-flash"


def pregen_voice_id() -> str:
    """两个人共用 Lex 的复刻音色。音色 ID 只放在本机 SHOWCASE_VOICE，不写入仓库。"""
    voice = os.getenv("SHOWCASE_VOICE", "").strip()
    if not voice:
        raise RuntimeError("SHOWCASE_VOICE is not set")
    return voice


def qa_system_prompt(question: str) -> str:
    return (
        "你是如意 SDK 现场演示里的讲解者。只根据下面的事实底稿回答。"
        "底稿没有的命令和适配关系不要编造，请观众去支持矩阵核对。\n\n"
        f"{load_facts()}\n\n"
        f"观众的问题：{question.strip()}"
    )


def load_deepseek_config() -> tuple[str, str, str]:
    """密钥优先读环境变量，否则读本机 Claude Code 配置。不把密钥写进仓库。"""
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    model = os.getenv("RUYI_QA_MODEL", "").strip()
    base = os.getenv("DEEPSEEK_BASE_URL", "").strip()
    if _CLAUDE_SETTINGS.is_file() and (not key or not model):
        try:
            env = json.loads(_CLAUDE_SETTINGS.read_text(encoding="utf-8")).get("env") or {}
        except (OSError, json.JSONDecodeError):
            env = {}
        key = key or str(env.get("ANTHROPIC_AUTH_TOKEN") or "").strip()
        model = model or str(env.get("ANTHROPIC_MODEL") or "").strip()
    return key, model or "deepseek-v4-flash", base or "https://api.deepseek.com"


def complete_with_deepseek(prompt: str) -> str:
    key, model, base = load_deepseek_config()
    if not key:
        raise RuntimeError("missing DeepSeek API key")
    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": "你只输出讲解者要说的话，不要标题，不要列提纲。"},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 400,
            "temperature": 0.3,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"DeepSeek HTTP {exc.code}: {detail}") from exc
    content = data["choices"][0]["message"]["content"]
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("empty DeepSeek reply")
    return content.strip()


def answer_question(message: str) -> dict[str, str | bool]:
    try:
        reply = complete_with_deepseek(qa_system_prompt(message))
    except Exception:
        return {"reply": QA_PAUSED_REPLY, "speaker": "guide", "llm": False}
    return {"reply": reply, "speaker": "guide", "llm": True}
