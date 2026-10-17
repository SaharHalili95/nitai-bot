import logging
import os

import anthropic
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

from prompts import SYSTEM_PROMPT, PROMPTS

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR)
CORS(app)

logger = logging.getLogger(__name__)
claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def ask_claude(prompt: str) -> str:
    message = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
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
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        data = {}
    product = str(data.get("product", "")).strip()
    sec = str(data.get("section", "")).strip()
    if not product or len(product) < 2:
        return jsonify({"error": "נא להזין שם מוצר תקין"}), 400
    if sec not in PROMPTS:
        return jsonify({"error": "סקציה לא תקינה"}), 400
    try:
        result = ask_claude(PROMPTS[sec](product))
        return jsonify({"product": product, "section": sec, "content": result})
    except Exception:
        # Do not echo provider errors (they can include request details) back to the browser.
        logger.exception("Claude request failed")
        return jsonify({"error": "שגיאה ביצירת התוכן. נסה שוב."}), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(debug=False, port=port, host="0.0.0.0")
