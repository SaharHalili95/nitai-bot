import os
import anthropic
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR)
CORS(app)

claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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

PROMPTS = {
    "short": lambda p: (
        f"חפש מידע עדכני על: {p}\n\n"
        "לאחר החיפוש, כתוב Short Description לדף מוצר WordPress בעברית:\n\n"
        "1. פסקת פתיחה שיווקית: <p> עם 2-3 משפטים המציגים את גולת הכותרת של המוצר</p>\n\n"
        "2. שלושה יתרונות מרכזיים:\n"
        "<ul>\n<li><strong>[יתרון 1]</strong> — תועלת מידית ללקוח</li>\n"
        "<li><strong>[יתרון 2]</strong> — תועלת מידית ללקוח</li>\n"
        "<li><strong>[יתרון 3]</strong> — תועלת מידית ללקוח</li>\n</ul>\n\n"
        "החזר HTML בלבד, ללא הסברים נוספים."
    ),
    "full": lambda p: (
        f"חפש מידע מעמיק על: {p}\n\n"
        "לאחר החיפוש, כתוב Full Description לדף מוצר WordPress בעברית — לפחות 200 מילים.\n\n"
        "מבנה חובה: 3 עד 5 פסקאות, כל אחת עם <h3> וכותרת משנה רלוונטית.\n"
        "בכל פסקה: הסבר לא רק מה יש — אלא איך זה עוזר למשתמש.\n"
        "שלב מונחים טכניים באנגלית בסוגריים כשרלוונטי.\n\n"
        "החזר HTML בלבד (<h3>, <p>, <strong>), ללא הסברים נוספים."
    ),
    "specs": lambda p: (
        f"חפש מפרט טכני מלא ומדויק של: {p}\n\n"
        "לאחר החיפוש, כתוב טבלת מפרט טכני מלאה בעברית:\n\n"
        "<table>\n<tr><th>מאפיין</th><th>נתון</th></tr>\n...\n</table>\n\n"
        "כלול: מידות, משקל, הספק, דירוג אנרגטי, נפח/קיבולת, חיבורים, מה כלול באריזה.\n"
        "אם ערך לא נמצא — כתוב 'לא צוין'. החזר HTML בלבד."
    ),
    "cons": lambda p: (
        f"חפש ביקורות ומשוב משתמשים על: {p}\n\n"
        "לאחר החיפוש, כתוב בעברית 2 חסרונות אמיתיים עם פתרון:\n\n"
        "<ul>\n"
        "<li><strong>⚠️ [שם החיסרון]</strong> — הסבר קצר<br>"
        "<strong>💡 פתרון:</strong> כיצד מתמודדים</li>\n"
        "<li><strong>⚠️ [שם החיסרון]</strong> — הסבר קצר<br>"
        "<strong>💡 פתרון:</strong> כיצד מתמודדים</li>\n</ul>\n\n"
        "החזר HTML בלבד, ללא הסברים נוספים."
    ),
}


def ask_claude(prompt: str) -> str:
    message = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}]
    )
    text_parts = [block.text for block in message.content if hasattr(block, "text")]
    return "\n".join(text_parts).strip()


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "search.html")


@app.route("/api/section", methods=["POST"])
def section():
    data = request.get_json()
    product = data.get("product", "").strip()
    sec = data.get("section", "").strip()
    if not product or len(product) < 2:
        return jsonify({"error": "נא להזין שם מוצר תקין"}), 400
    if sec not in PROMPTS:
        return jsonify({"error": "סקציה לא תקינה"}), 400
    try:
        result = ask_claude(PROMPTS[sec](product))
        return jsonify({"product": product, "section": sec, "content": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(debug=False, port=port, host="0.0.0.0")
