import html
import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import anthropic

from prompts import PROMPTS, SYSTEM_PROMPT, strip_code_fence

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Telegram limits callback_data to 64 bytes, and Hebrew product names take two bytes
# per letter, so buttons carry a short key into this per-chat store instead of the name.
MAX_PRODUCTS_PER_CHAT = 20
TELEGRAM_LIMIT = 4096
CHUNK_SIZE = 3800

SECTION_NAMES = {
    "short": "📋 תיאור קצר",
    "full": "📄 תיאור מלא",
    "specs": "🔧 מפרט טכני",
    "cons": "⚠️ חסרונות ופתרונות",
    "all": "📦 דף מוצר מלא",
}


def remember_product(chat_data: dict, product: str) -> str:
    products = chat_data.setdefault("products", {})
    key = str(chat_data.get("next_key", 0))
    chat_data["next_key"] = int(key) + 1
    products[key] = product
    while len(products) > MAX_PRODUCTS_PER_CHAT:
        products.pop(next(iter(products)))
    return key


def parse_callback(data: str, chat_data: dict) -> tuple[str, str] | None:
    """Returns (section, product) for a button press, or None if the button is stale or invalid."""
    section, sep, key = data.partition("|")
    if not sep or section not in SECTION_NAMES:
        return None
    product = chat_data.get("products", {}).get(key)
    return (section, product) if product else None


def split_message(parts: list[str], separator: str, limit: int = CHUNK_SIZE) -> list[str]:
    """Joins parts into messages under the limit, splitting any single part that is too long."""
    pieces = []
    for part in parts:
        pieces.extend(part[i:i + limit] for i in range(0, max(len(part), 1), limit))
    chunks, current = [], ""
    for piece in pieces:
        block = (separator if current else "") + piece
        if current and len(current) + len(block) > limit:
            chunks.append(current)
            current = piece
        else:
            current += block
    if current:
        chunks.append(current)
    return chunks


def build_prompt(product: str, section: str) -> str:
    return PROMPTS[section](product)


async def ask_claude(prompt: str) -> str:
    try:
        message = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}]
        )
        # Extract text from response (may contain tool use blocks)
        text_parts = [block.text for block in message.content if hasattr(block, "text")]
        return strip_code_fence("\n".join(text_parts)) or "לא נמצא מידע על המוצר."
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return "אירעה שגיאה בעת יצירת התוכן. נסה שוב."


def get_section_keyboard(key: str) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📋 תיאור קצר", callback_data=f"short|{key}"),
            InlineKeyboardButton("📄 תיאור מלא", callback_data=f"full|{key}"),
        ],
        [
            InlineKeyboardButton("🔧 מפרט טכני", callback_data=f"specs|{key}"),
            InlineKeyboardButton("⚠️ חסרונות ופתרונות", callback_data=f"cons|{key}"),
        ],
        [
            InlineKeyboardButton("🔄 הכל (WordPress)", callback_data=f"all|{key}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome = (
        "👋 שלום! אני *Nitai* - הבוט שלך למידע על מוצרי חשמל.\n\n"
        "🔍 *איך משתמשים?*\n"
        "פשוט שלח לי שם מוצר, דגם, או מק\"ט ואני אביא לך מידע מפורט.\n\n"
        "📌 *דוגמאות:*\n"
        "• `Samsung Galaxy S24`\n"
        "• `מקרר בוש KGN39AIBT`\n"
        "• `מייבש שיער פיליפס BHD350`\n\n"
        "שלח מוצר ונתחיל! 🚀"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def handle_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    product = update.message.text.strip()

    if len(product) < 2:
        await update.message.reply_text("⚠️ נא להזין שם מוצר תקין.")
        return

    key = remember_product(context.chat_data, product)
    await update.message.reply_text(
        f"🔍 מחפש מידע על: <b>{html.escape(product)}</b>\n\nבחר את המידע שתרצה לקבל:",
        parse_mode="HTML",
        reply_markup=get_section_keyboard(key)
    )


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    parsed = parse_callback(query.data or "", context.chat_data)
    if parsed is None:
        await query.edit_message_text("⌛ הכפתור הזה כבר לא פעיל. שלח את שם המוצר שוב.")
        return
    section, product = parsed
    safe_product = html.escape(product)
    key = query.data.partition("|")[2]

    await query.edit_message_text(
        f"⏳ מכין {SECTION_NAMES[section]} עבור <b>{safe_product}</b>...",
        parse_mode="HTML"
    )

    if section == "all":
        section_labels = {
            "short": "📋 SHORT DESCRIPTION",
            "full": "📄 FULL DESCRIPTION",
            "specs": "🔧 TECHNICAL SPECIFICATIONS",
            "cons": "⚠️ חסרונות ופתרונות",
        }
        parts = [f"<b>📦 דף מוצר WordPress — {safe_product}</b>"]
        for s in section_labels:
            content = await ask_claude(build_prompt(product, s))
            parts.append(f"<b>{section_labels[s]}</b>\n\n{content}")

        chunks = split_message(parts, "\n\n" + "─" * 30 + "\n\n")
        await query.edit_message_text(chunks[0], parse_mode="HTML")
        for chunk in chunks[1:]:
            await query.message.reply_text(chunk, parse_mode="HTML")
        await query.message.reply_text(
            f"✅ דף מוצר מלא עבור <b>{safe_product}</b> מוכן להדבקה ב-WordPress.",
            parse_mode="HTML",
            reply_markup=get_section_keyboard(key)
        )
    else:
        content = await ask_claude(build_prompt(product, section))
        response = f"<b>{SECTION_NAMES[section]} — {safe_product}</b>\n\n{content}"
        await query.edit_message_text(
            response[:TELEGRAM_LIMIT],
            parse_mode="HTML",
            reply_markup=get_section_keyboard(key)
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)


def main() -> None:
    if not TELEGRAM_TOKEN:
        raise ValueError("חסר TELEGRAM_BOT_TOKEN ב-.env")
    if not ANTHROPIC_API_KEY:
        raise ValueError("חסר ANTHROPIC_API_KEY ב-.env")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product))

    logger.info("Nitai Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
