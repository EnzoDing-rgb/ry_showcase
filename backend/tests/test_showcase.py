"""离线单测：如意 SDK 现场演示的固定故事与提问兜底（不调用大模型、不合成语音）。"""

import base64
import json

from backend.showcase import (
    QA_PAUSED_REPLY,
    STORY,
    answer_aloud,
    answer_question,
    load_facts,
    qa_system_prompt,
    synthesize_reply,
)


def test_story_has_six_alternating_turns():
    assert len(STORY) == 6
    assert [turn.speaker for turn in STORY] == [
        "developer",
        "guide",
        "developer",
        "guide",
        "developer",
        "guide",
    ]
    assert [turn.audio for turn in STORY] == [f"/audio/ruyi-{i:02d}.mp3" for i in range(1, 7)]


def test_story_shows_many_boards_not_one_product():
    text = "\n".join(turn.text for turn in STORY)
    for name in ("Milk-V Duo", "VisionFive", "荔枝派", "BPI-F3", "DC-ROMA", "HiFive"):
        assert name in text
    assert "ruyi venv" in text
    assert "ruyi device provision" in text
    assert STORY[-1].speaker == "guide"
    assert "问" in STORY[-1].text


def test_facts_cover_positioning_commands_and_boards():
    facts = load_facts()
    assert "一体化" in facts
    assert "ruyi install" in facts
    assert "ruyi venv" in facts
    assert "ruyi device provision" in facts
    assert "matrix.ruyisdk.org" in facts
    for name in ("Milk-V Duo", "VisionFive 2", "荔枝派 4A", "BPI-F3", "HiFive"):
        assert name in facts
    assert "不要编造" in facts


def test_answer_uses_model_reply(monkeypatch):
    seen: dict[str, str] = {}

    def fake(prompt: str) -> str:
        seen["prompt"] = prompt
        return "Duo 和 VisionFive 都用 ruyi device provision 按板子装系统。"

    monkeypatch.setattr("backend.showcase.complete_with_deepseek", fake)
    result = answer_question("Duo 怎么装？")
    assert result["llm"] is True
    assert result["speaker"] == "guide"
    assert "device provision" in result["reply"]
    assert "Duo 怎么装" in seen["prompt"]
    assert "不要编造" in seen["prompt"]


def test_answer_falls_back_when_model_fails(monkeypatch):
    def boom(_prompt: str) -> str:
        raise RuntimeError("down")

    monkeypatch.setattr("backend.showcase.complete_with_deepseek", boom)
    result = answer_question("随便问问")
    assert result["llm"] is False
    assert result["speaker"] == "guide"
    assert result["reply"] == QA_PAUSED_REPLY


def test_answer_aloud_returns_mp3_for_the_reply(monkeypatch):
    monkeypatch.setattr("backend.showcase.complete_with_deepseek", lambda _prompt: "就用 ruyi venv。")
    monkeypatch.setattr("backend.showcase.synthesize_reply", lambda text: b"ID3" + text.encode("utf-8") + b"x" * 40)
    result = answer_aloud("怎么建环境？")
    audio = base64.b64decode(str(result["audio_base64"]))
    assert result["spoken"] is True
    assert audio.startswith(b"ID3")
    assert "ruyi venv" in audio.decode("utf-8", errors="ignore")


def test_answer_aloud_keeps_text_when_speech_fails(monkeypatch):
    monkeypatch.setattr("backend.showcase.complete_with_deepseek", lambda _prompt: "文字还在。")

    def boom(_text: str) -> bytes:
        raise RuntimeError("tts down")

    monkeypatch.setattr("backend.showcase.synthesize_reply", boom)
    result = answer_aloud("问一句")
    assert result["spoken"] is False
    assert result["audio_base64"] == ""
    assert result["reply"] == "文字还在。"
    assert result["llm"] is True


def test_synthesize_reply_downloads_the_mp3(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("SHOWCASE_VOICE", "voice-test")
    monkeypatch.setenv("SHOWCASE_TTS_MODEL", "qwen-audio-3.1-tts-flash")
    seen: list[str] = []

    class _Body:
        def __init__(self, payload: bytes):
            self._payload = payload

        def read(self) -> bytes:
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_open(request, timeout=0):
        del timeout
        url = request if isinstance(request, str) else request.full_url
        seen.append(url)
        if url.endswith("SpeechSynthesizer"):
            body = json.loads(request.data.decode("utf-8"))
            assert body["input"]["voice"] == "voice-test"
            assert body["input"]["text"] == "你好"
            assert body["model"] == "qwen-audio-3.1-tts-flash"
            encoded = json.dumps({"output": {"audio": {"url": "https://example.test/a.mp3"}}}).encode()
            return _Body(encoded)
        return _Body(b"ID3" + b"y" * 1200)

    monkeypatch.setattr("backend.showcase.urllib.request.urlopen", fake_open)
    audio = synthesize_reply("你好")
    assert audio.startswith(b"ID3")
    assert seen == [
        "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer",
        "https://example.test/a.mp3",
    ]


def test_qa_prompt_includes_facts_and_the_question():
    prompt = qa_system_prompt("VisionFive 2 和 Duo 是不是同一条 ruyi？")
    assert "matrix.ruyisdk.org" in prompt
    assert "VisionFive 2 和 Duo" in prompt
    assert "不要编造" in prompt
