"""
Shared system prompt and content templates for Nitai.

Used by both bot.py (Telegram) and server.py (web UI) - previously this
whole file was duplicated verbatim in both entry points.
"""

import re

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


def _short(product: str) -> str:
    return (
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
    )


def _full(product: str) -> str:
    return (
        f"חפש מידע מעמיק על: {product}\n\n"
        "לאחר החיפוש, כתוב Full Description לדף מוצר WordPress בעברית — לפחות 200 מילים.\n\n"
        "מבנה חובה: 3 עד 5 פסקאות, כל אחת עם <h3> וכותרת משנה רלוונטית.\n"
        "דוגמאות לכותרות: 'ביצועים מרשימים', 'עיצוב חכם', 'חוויית שימוש', 'טכנולוגיה מתקדמת'\n\n"
        "בכל פסקה: הסבר לא רק מה יש — אלא איך זה עוזר למשתמש.\n"
        "שלב מונחים טכניים באנגלית בסוגריים כשרלוונטי.\n\n"
        "החזר HTML בלבד (<h3>, <p>, <strong>), ללא הסברים נוספים."
    )


def _specs(product: str) -> str:
    return (
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
    )


def _cons(product: str) -> str:
    return (
        f"חפש ביקורות ומשוב משתמשים על: {product}\n\n"
        "לאחר החיפוש, כתוב בעברית 2 חסרונות אמיתיים עם פתרון לכל אחד:\n\n"
        "<ul>\n"
        "<li><strong>⚠️ [שם החיסרון]</strong> — הסבר קצר<br>"
        "<strong>💡 פתרון:</strong> כיצד מתמודדים</li>\n"
        "<li><strong>⚠️ [שם החיסרון]</strong> — הסבר קצר<br>"
        "<strong>💡 פתרון:</strong> כיצד מתמודדים</li>\n"
        "</ul>\n\n"
        "החזר HTML בלבד, ללא הסברים נוספים."
    )


def strip_code_fence(text: str) -> str:
    """Claude sometimes wraps the HTML in ```html fences, which would be pasted into WordPress as-is."""
    text = text.strip()
    match = re.fullmatch(r"```[a-zA-Z]*\s*\n(.*?)\n?\s*```", text, re.DOTALL)
    return match.group(1).strip() if match else text


PROMPTS = {
    "short": _short,
    "full": _full,
    "specs": _specs,
    "cons": _cons,
}
