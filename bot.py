import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import anthropic

from prompts import SYSTEM_PROMPT, PROMPTS

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

user_searches = {}


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
        return "\n".join(text_parts).strip() or "לא נמצא מידע על המוצר."
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return "אירעה שגיאה בעת יצירת התוכן. נסה שוב."


def get_section_keyboard(product: str) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📋 תיאור קצר", callback_data=f"short|{product}"),
            InlineKeyboardButton("📄 תיאור מלא", callback_data=f"full|{product}"),
        ],
        [
            InlineKeyboardButton("🔧 מפרט טכני", callback_data=f"specs|{product}"),
            InlineKeyboardButton("⚠️ חסרונות ופתרונות", callback_data=f"cons|{product}"),
        ],
        [
            InlineKeyboardButton("🔄 הכל (WordPress)", callback_data=f"all|{product}"),
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

    await update.message.reply_text(
        f"🔍 מחפש מידע על: *{product}*\n\nבחר את המידע שתרצה לקבל:",
        parse_mode="Markdown",
        reply_markup=get_section_keyboard(product)
    )


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data
    if "|" not in data:
        return

    section, product = data.split("|", 1)

    section_names = {
        "short": "📋 תיאור קצר",
        "full": "📄 תיאור מלא",
        "specs": "🔧 מפרט טכני",
        "cons": "⚠️ חסרונות ופתרונות",
        "all": "📦 דף מוצר מלא",
    }

    await query.edit_message_text(
        f"⏳ מכין {section_names.get(section, 'מידע')} עבור *{product}*...",
        parse_mode="Markdown"
    )

    if section == "all":
        sections = ["short", "full", "specs", "cons"]
        section_labels = {
            "short": "📋 SHORT DESCRIPTION",
            "full": "📄 FULL DESCRIPTION",
            "specs": "🔧 TECHNICAL SPECIFICATIONS",
            "cons": "⚠️ חסרונות ופתרונות",
        }

        separator = "\n\n" + "─" * 30 + "\n\n"
        parts = [f"<b>📦 דף מוצר WordPress — {product}</b>"]

        for s in sections:
            prompt = build_prompt(product, s)
            content = await ask_claude(prompt)
            parts.append(f"<b>{section_labels[s]}</b>\n\n{content}")

        full_response = separator.join(parts)

        # Send in chunks (Telegram HTML limit ~4096)
        chunks = []
        current = ""
        for part in parts:
            block = (separator if current else "") + part
            if len(current) + len(block) > 3800:
                chunks.append(current)
                current = part
            else:
                current += block
        if current:
            chunks.append(current)

        await query.edit_message_text(chunks[0], parse_mode="HTML")
        for chunk in chunks[1:]:
            await query.message.reply_text(chunk, parse_mode="HTML")
        # Re-send keyboard on last message
        await query.message.reply_text(
            f"✅ דף מוצר מלא עבור <b>{product}</b> מוכן להדבקה ב-WordPress.",
            parse_mode="HTML",
            reply_markup=get_section_keyboard(product)
        )
    else:
        prompt = build_prompt(product, section)
        content = await ask_claude(prompt)

        header = section_names.get(section, "מידע")
        response = f"<b>{header} — {product}</b>\n\n{content}"

        await query.edit_message_text(
            response[:4096],
            parse_mode="HTML",
            reply_markup=get_section_keyboard(product)
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
