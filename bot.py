import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import anthropic

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


SYSTEM_PROMPT = """System Role: NitaiJR Content Architect for eCommerce

אתה מומחה תוכן בכיר לעולם מוצרי החשמל והאלקטרוניקה.
תפקידך לייצר דפי מוצר עשירים, שיווקיים וטכניים בעברית על סמך שם דגם או מק"ט.
התוכן מיועד להטמעה ב-WordPress ומעוצב בסטנדרט של רשתות מובילות (באג/KSP).

כללים:
- חפש תמיד מידע עדכני ומדויק לפני כתיבה
- HTML Ready: השתמש בתגיות <h3>, <p>, <ul>, <li>, <strong>
- שפה: עברית מקצועית. מונחים טכניים באנגלית בסוגריים
- אל תעתיק — צור תוכן מקורי שנשמע כמומחה מוצר
- דיוק: הסתמך על נתונים ריאליים. אם הדגם לא מוכר — ציין זאת"""


def build_prompt(product: str, section: str) -> str:
    prompts = {
        "short": (
            f"חפש מידע עדכני על: {product}\n\n"
            "לאחר החיפוש, כתוב Short Description לדף מוצר WordPress בעברית:\n\n"
            "1. פסקת פתיחה שיווקית: <p> עם 2-3 משפטים המציגים את גולת הכותרת של המוצר</p>\n\n"
            "2. שלושה יתרונות מרכזיים:\n"
            "<ul>\n"
            "<li><strong>[יתרון 1]</strong> — תועלת מידית ללקוח</li>\n"
            "<li><strong>[יתרון 2]</strong> — תועלת מידית ללקוח</li>\n"
            "<li><strong>[יתרון 3]</strong> — תועלת מידית ללקוח</li>\n"
            "</ul>\n\n"
            "החזר HTML בלבד, ללא הסברים נוספים."
        ),
        "full": (
            f"חפש מידע מעמיק על: {product}\n\n"
            "לאחר החיפוש, כתוב Full Description לדף מוצר WordPress בעברית — לפחות 200 מילים.\n\n"
            "מבנה חובה: 3 עד 5 פסקאות, כל אחת עם <h3> וכותרת משנה רלוונטית.\n"
            "דוגמאות לכותרות: 'ביצועים מרשימים', 'עיצוב חכם', 'חוויית שימוש', 'טכנולוגיה מתקדמת'\n\n"
            "בכל פסקה: הסבר לא רק מה יש — אלא איך זה עוזר למשתמש.\n"
            "שלב מונחים טכניים באנגלית בסוגריים כשרלוונטי.\n\n"
            "החזר HTML בלבד (<h3>, <p>, <strong>), ללא הסברים נוספים."
        ),
        "specs": (
            f"חפש מפרט טכני מלא ומדויק של: {product}\n\n"
            "לאחר החיפוש, כתוב טבלת מפרט טכני מלאה בעברית בפורמט HTML:\n\n"
            "<table>\n"
            "<tr><th>מאפיין</th><th>נתון</th></tr>\n"
            "<tr><td>דגם</td><td>[ערך]</td></tr>\n"
            "...\n"
            "</table>\n\n"
            "כלול: מידות (גובה/רוחב/עומק), משקל, הספק, דירוג אנרגטי, נפח/קיבולת, "
            "תוכניות עבודה, חיבורים, מה כלול באריזה, וכל נתון טכני רלוונטי.\n"
            "אם ערך לא נמצא — כתוב 'לא צוין'.\n"
            "החזר HTML בלבד, ללא הסברים נוספים."
        ),
        "cons": (
            f"חפש ביקורות ומשוב משתמשים על: {product}\n\n"
            "לאחר החיפוש, כתוב בעברית 2 חסרונות אמיתיים עם פתרון לכל אחד:\n\n"
            "<ul>\n"
            "<li><strong>⚠️ [שם החיסרון]</strong> — הסבר קצר<br>"
            "<strong>💡 פתרון:</strong> כיצד מתמודדים</li>\n"
            "<li><strong>⚠️ [שם החיסרון]</strong> — הסבר קצר<br>"
            "<strong>💡 פתרון:</strong> כיצד מתמודדים</li>\n"
            "</ul>\n\n"
            "החזר HTML בלבד, ללא הסברים נוספים."
        ),
    }
    return prompts[section]


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
