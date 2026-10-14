"""离线单测：如意 SDK 现场演示的固定故事与提问兜底（不调用大模型、不合成语音）。"""

from backend.showcase import (
    QA_PAUSED_REPLY,
    STORY,
    answer_question,
    load_facts,
    qa_system_prompt,
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


def test_qa_prompt_includes_facts_and_the_question():
    prompt = qa_system_prompt("VisionFive 2 和 Duo 是不是同一条 ruyi？")
    assert "matrix.ruyisdk.org" in prompt
    assert "VisionFive 2 和 Duo" in prompt
    assert "不要编造" in prompt
