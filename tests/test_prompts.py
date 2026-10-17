import pytest

from prompts import PROMPTS, SYSTEM_PROMPT, strip_code_fence


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


@pytest.mark.parametrize(
    "raw",
    [
        "```html\n<p>שלום</p>\n```",
        "```\n<p>שלום</p>\n```",
        "  ```html\n<p>שלום</p>```  ",
        "<p>שלום</p>",
    ],
)
def test_code_fences_are_removed(raw):
    assert strip_code_fence(raw) == "<p>שלום</p>"


def test_fences_inside_the_text_are_kept():
    text = "<p>a</p>\n```js\nx\n```\n<p>b</p>"
    assert strip_code_fence(text) == text
