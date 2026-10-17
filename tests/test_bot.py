from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import bot


def test_buttons_fit_telegrams_64_byte_limit_even_for_long_hebrew_names():
    chat = {}
    key = bot.remember_product(chat, "מקרר בוש דו דלתי עם מקפיא תחתון וצג דיגיטלי KGN39AIBT")
    for row in bot.get_section_keyboard(key).inline_keyboard:
        for button in row:
            assert len(button.callback_data.encode()) <= 64


def test_button_press_returns_the_remembered_product():
    chat = {}
    key = bot.remember_product(chat, "Philips BHD350")
    assert bot.parse_callback(f"specs|{key}", chat) == ("specs", "Philips BHD350")


def test_each_product_gets_its_own_key():
    chat = {}
    a = bot.remember_product(chat, "A")
    b = bot.remember_product(chat, "B")
    assert a != b
    assert bot.parse_callback(f"short|{a}", chat)[1] == "A"


def test_old_products_are_forgotten():
    chat = {}
    first = bot.remember_product(chat, "first")
    for i in range(bot.MAX_PRODUCTS_PER_CHAT):
        bot.remember_product(chat, f"p{i}")
    assert len(chat["products"]) == bot.MAX_PRODUCTS_PER_CHAT
    assert bot.parse_callback(f"short|{first}", chat) is None


@pytest.mark.parametrize("data", ["", "short", "hack|0", "short|999"])
def test_invalid_or_stale_buttons_are_rejected(data):
    chat = {}
    bot.remember_product(chat, "x")
    assert bot.parse_callback(data, chat) is None


def test_split_keeps_short_messages_together():
    assert bot.split_message(["a", "b"], "|", limit=10) == ["a|b"]


def test_split_starts_a_new_chunk_when_full():
    assert bot.split_message(["aaaa", "bbbb", "cc"], "|", limit=9) == ["aaaa|bbbb", "cc"]


def test_split_breaks_a_single_part_that_is_too_long():
    chunks = bot.split_message(["x" * 25], "|", limit=10)
    assert chunks == ["x" * 10, "x" * 10, "x" * 5]
    assert all(len(c) <= 10 for c in chunks)


def test_split_never_exceeds_telegrams_limit():
    parts = ["header", "y" * 9000, "z" * 3000]
    assert all(len(c) <= bot.TELEGRAM_LIMIT for c in bot.split_message(parts, "\n\n"))


def make_update(text):
    message = SimpleNamespace(text=text, reply_text=AsyncMock())
    return SimpleNamespace(message=message), SimpleNamespace(chat_data={})


@pytest.mark.asyncio
async def test_short_input_is_rejected():
    update, context = make_update(" a ")
    await bot.handle_product(update, context)
    assert "נא להזין" in update.message.reply_text.call_args.args[0]


@pytest.mark.asyncio
async def test_product_name_is_html_escaped():
    update, context = make_update("<b>TV</b> & *stuff*")
    await bot.handle_product(update, context)
    text = update.message.reply_text.call_args.args[0]
    assert "&lt;b&gt;TV&lt;/b&gt; &amp; *stuff*" in text
    assert update.message.reply_text.call_args.kwargs["parse_mode"] == "HTML"


def make_query(data):
    query = SimpleNamespace(data=data, answer=AsyncMock(), edit_message_text=AsyncMock(),
                            message=SimpleNamespace(reply_text=AsyncMock()))
    return SimpleNamespace(callback_query=query), query


@pytest.mark.asyncio
async def test_single_section_is_generated_for_the_product(monkeypatch):
    ask = AsyncMock(return_value="<p>content</p>")
    monkeypatch.setattr(bot, "ask_claude", ask)
    chat = {}
    key = bot.remember_product(chat, "Samsung S24")
    update, query = make_query(f"short|{key}")

    await bot.handle_button(update, SimpleNamespace(chat_data=chat))

    assert "Samsung S24" in ask.call_args.args[0]
    final = query.edit_message_text.call_args_list[-1]
    assert "<p>content</p>" in final.args[0]
    assert final.kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_all_sections_are_generated_and_sent_in_chunks(monkeypatch):
    ask = AsyncMock(return_value="w" * 3000)
    monkeypatch.setattr(bot, "ask_claude", ask)
    chat = {}
    key = bot.remember_product(chat, "LG OLED")
    update, query = make_query(f"all|{key}")

    await bot.handle_button(update, SimpleNamespace(chat_data=chat))

    assert ask.await_count == 4
    sent = [query.edit_message_text.call_args_list[-1].args[0]] + [c.args[0] for c in query.message.reply_text.call_args_list]
    assert all(len(text) <= bot.TELEGRAM_LIMIT for text in sent)
    assert "מוכן להדבקה" in sent[-1]


@pytest.mark.asyncio
async def test_stale_button_asks_to_search_again(monkeypatch):
    monkeypatch.setattr(bot, "ask_claude", AsyncMock())
    update, query = make_query("short|42")
    await bot.handle_button(update, SimpleNamespace(chat_data={}))
    assert "כבר לא פעיל" in query.edit_message_text.call_args.args[0]
    bot.ask_claude.assert_not_awaited()


@pytest.mark.asyncio
async def test_claude_errors_become_a_friendly_message(monkeypatch):
    monkeypatch.setattr(bot.claude.messages, "create", MagicMock(side_effect=RuntimeError("boom")))
    assert "שגיאה" in await bot.ask_claude("x")


@pytest.mark.asyncio
async def test_only_text_blocks_are_returned(monkeypatch):
    response = SimpleNamespace(content=[SimpleNamespace(type="server_tool_use"), SimpleNamespace(text="שלום")])
    monkeypatch.setattr(bot.claude.messages, "create", MagicMock(return_value=response))
    assert await bot.ask_claude("x") == "שלום"
