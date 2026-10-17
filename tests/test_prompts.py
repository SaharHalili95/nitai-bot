import pytest

from prompts import PROMPTS, SYSTEM_PROMPT


def test_all_four_sections_exist():
    assert set(PROMPTS) == {"short", "full", "specs", "cons"}


@pytest.mark.parametrize("section", ["short", "full", "specs", "cons"])
def test_each_prompt_names_the_product(section):
    assert "Bosch KGN39AIBT" in PROMPTS[section]("Bosch KGN39AIBT")


@pytest.mark.parametrize("section", ["short", "full", "specs", "cons"])
def test_each_prompt_asks_for_html_only(section):
    assert "החזר HTML בלבד" in PROMPTS[section]("x")


def test_full_description_requires_200_words():
    assert "200 מילים" in PROMPTS["full"]("x")


def test_specs_ask_for_a_table_and_missing_values():
    prompt = PROMPTS["specs"]("x")
    assert "<table>" in prompt
    assert "לא צוין" in prompt


def test_system_prompt_requires_hebrew_and_html():
    assert "עברית" in SYSTEM_PROMPT
    assert "HTML" in SYSTEM_PROMPT
