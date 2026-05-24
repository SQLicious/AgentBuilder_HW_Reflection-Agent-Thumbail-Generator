from thumbnail_agent.prompts import CRITIC_SYSTEM, PROMPT_WRITER_SYSTEM


def test_prompt_writer_forbids_cliches_and_requires_visual_elements():
    text = PROMPT_WRITER_SYSTEM.lower()
    assert "delve" not in text
    assert "focal subject" in text
    assert "text overlay" in text
    assert "color palette" in text


def test_critic_enforces_strict_scoring():
    assert "5" in CRITIC_SYSTEM
    assert "9" in CRITIC_SYSTEM
    assert "specific improvements" in CRITIC_SYSTEM.lower()
