"""Flask REST API for the English Learning project."""
import hmac
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT.parent / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, jsonify, request
from sqlalchemy import or_
from app.database import Card, HardWord, Word, configure_database, db
from app.utils import add_custom_word, add_hard_word, bind_chat_ids, delete_custom_word, get_total_cards, initialize_database, list_all_custom_words, list_course_snapshots, list_custom_words, list_dictionary, load_progress, load_words, save_progress, start_new_course, update_custom_word

app = Flask(__name__)
configure_database(app)
with app.app_context(): initialize_database()


def _admin_password(): return os.getenv("ADMIN_PASSWORD", "")
def _is_admin_request(): return bool(_admin_password()) and hmac.compare_digest(request.headers.get("X-Admin-Password", ""), _admin_password())
def _admin_required():
    if not _admin_password(): return jsonify({"success": False, "message": "ADMIN_PASSWORD не настроен"}), 503
    if not _is_admin_request(): return jsonify({"success": False, "message": "Неверный пароль администратора"}), 401
    return None
def _word_payload(item): return {"id": item.id, "card_id": item.card_id, "en": item.en, "ru": item.ru}

@app.after_request
def add_cors_headers(response):
    local_origins = "http://127.0.0.1:8000,http://localhost:8000"
    allowed = {x.strip().rstrip("/") for x in os.getenv("CORS_ORIGINS", os.getenv("CORS_ORIGIN", local_origins)).split(",") if x.strip()}
    origin = request.headers.get("Origin", "").rstrip("/")
    if origin and origin in allowed: response.headers["Access-Control-Allow-Origin"] = origin; response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Admin-Password"
    return response

@app.get("/")
def index(): return jsonify({"service": "English Learning API", "health": "/api/health"})
@app.get("/api/all-words")
def api_all_words(): return jsonify(load_words())
@app.get("/api/dictionary")
def api_dictionary(): return jsonify(list_dictionary(request.args.get("page", 1, type=int) or 1, min(max(request.args.get("per_page", 10, type=int) or 10, 1), 50)))

@app.route("/api/admin/login", methods=["POST", "OPTIONS"])
def api_admin_login():
    if request.method == "OPTIONS": return "", 204
    if not _admin_password(): return jsonify({"success": False, "message": "ADMIN_PASSWORD не настроен"}), 503
    if not hmac.compare_digest(str((request.get_json(silent=True) or {}).get("password", "")), _admin_password()): return jsonify({"success": False, "message": "Неверный пароль"}), 401
    return jsonify({"success": True})

@app.route("/api/admin/words", methods=["GET", "POST", "OPTIONS"])
def api_admin_words():
    if request.method == "OPTIONS": return "", 204
    denied = _admin_required()
    if denied: return denied
    if request.method == "POST":
        data = request.get_json(silent=True) or {}; en = str(data.get("en", "")).strip(); ru = str(data.get("ru", "")).strip()
        try: card_id = int(data.get("card_id"))
        except (TypeError, ValueError): return jsonify({"success": False, "message": "Укажи номер карточки"}), 400
        if not en or not ru: return jsonify({"success": False, "message": "Заполни слово и перевод"}), 400
        card = Card.query.filter(Card.id == card_id, Card.id != 99).first()
        if not card: return jsonify({"success": False, "message": "Карточка не найдена"}), 404
        if Word.query.filter(db.func.lower(Word.en) == en.casefold()).first(): return jsonify({"success": False, "message": "Такое английское слово уже есть"}), 409
        item = Word(card_id=card.id, en=en, ru=ru); db.session.add(item); db.session.commit(); return jsonify({"success": True, "item": _word_payload(item)}), 201
    search = str(request.args.get("search", "")).strip(); page = max(request.args.get("page", 1, type=int) or 1, 1); per_page = min(max(request.args.get("per_page", 25, type=int) or 25, 1), 100)
    query = Word.query.join(Card, Word.card_id == Card.id).filter(Card.id != 99)
    if search: query = query.filter(or_(Word.en.ilike(f"%{search}%"), Word.ru.ilike(f"%{search}%")))
    query = query.order_by(Card.id, Word.id); total = query.count(); pages = max(1, (total + per_page - 1)//per_page); page = min(page, pages)
    return jsonify({"success": True, "items": [_word_payload(i) for i in query.offset((page-1)*per_page).limit(per_page).all()], "page": page, "per_page": per_page, "total": total, "total_pages": pages})

@app.route("/api/admin/words/<int:word_id>", methods=["PATCH", "DELETE", "OPTIONS"])
def api_admin_word(word_id):
    if request.method == "OPTIONS": return "", 204
    denied = _admin_required()
    if denied: return denied
    item = Word.query.join(Card, Word.card_id == Card.id).filter(Word.id == word_id, Card.id != 99).first()
    if not item: return jsonify({"success": False, "message": "Слово не найдено"}), 404
    if request.method == "DELETE": HardWord.query.filter_by(word_en=item.en).delete(synchronize_session=False); db.session.delete(item); db.session.commit(); return jsonify({"success": True})
    data = request.get_json(silent=True) or {}; en = str(data.get("en", item.en)).strip(); ru = str(data.get("ru", item.ru)).strip()
    if not en or not ru: return jsonify({"success": False, "message": "Слово и перевод не могут быть пустыми"}), 400
    duplicate = Word.query.filter(db.func.lower(Word.en) == en.casefold(), Word.id != item.id).first()
    if duplicate: return jsonify({"success": False, "message": "Такое английское слово уже есть"}), 409
    old_en = item.en; item.en = en; item.ru = ru
    if old_en != en: HardWord.query.filter_by(word_en=old_en).update({"word_en": en}, synchronize_session=False)
    db.session.commit(); return jsonify({"success": True, "item": _word_payload(item)})

@app.get("/api/current-card")
def api_current_card():
    progress = load_progress(request.args.get("chat_id", "default"))
    if progress["finished"]: return jsonify({"finished": True, "message": "🎉 Вы прошли весь основной словарь — 300 слов"})
    card = next((x for x in load_words()["cards"] if x["id"] == progress["current_card"]), None)
    return jsonify({"finished": False, "card": card, "progress": {"current_card": progress["current_card"], "total_cards": get_total_cards(), "completed": len(progress["completed_cards"]), "course_number": progress["course_number"]}})

@app.route("/api/progress", methods=["GET", "PUT"])
def api_progress():
    data = request.get_json(silent=True) or {}; chat_id = request.args.get("chat_id") or data.get("chat_id", "default")
    if request.method == "PUT": save_progress(chat_id, data)
    p = load_progress(chat_id); total = p["total_correct"] + p["total_wrong"]
    return jsonify({**p, "total_cards": get_total_cards(), "accuracy": round(p["total_correct"] / total * 100, 1) if total else 0, "custom_words_count": len(p["custom_words"])})

@app.post("/api/check-answer")
def api_check_answer():
    data = request.get_json(silent=True) or {}; chat_id = request.args.get("chat_id") or data.get("chat_id", "default"); p = load_progress(chat_id); correct = bool(data.get("is_correct", False)); word = str(data.get("word_en", "")).strip()
    if correct: p["total_correct"] += 1; p["streak"] += 1; p["best_streak"] = max(p["best_streak"], p["streak"])
    else: p["total_wrong"] += 1; p["streak"] = 0; add_hard_word(chat_id, word)
    save_progress(chat_id, p); return jsonify({"correct": correct, "streak": p["streak"], "total_correct": p["total_correct"], "total_wrong": p["total_wrong"]})

@app.post("/api/hard-word")
def api_hard_word():
    data = request.get_json(silent=True) or {}
    chat_id = str(data.get("chat_id", "")).strip()
    word_en = str(data.get("word_en", "")).strip()
    if not chat_id or not word_en:
        return jsonify({"success": False, "message": "chat_id и word_en обязательны"}), 400
    add_hard_word(chat_id, word_en)
    return jsonify({"success": True})

@app.post("/api/complete-card")
def api_complete_card():
    data = request.get_json(silent=True) or {}; chat_id = request.args.get("chat_id") or data.get("chat_id", "default"); p = load_progress(chat_id); current = p["current_card"]
    if current not in p["completed_cards"]: p["completed_cards"].append(current)
    p["current_card"] += 1; total = get_total_cards()
    if p["current_card"] > total: p["finished"] = True; p["current_card"] = total
    save_progress(chat_id, p); return jsonify({"has_next": not p["finished"], "finished": p["finished"], "current_card": p["current_card"], "completed": len(p["completed_cards"])})

@app.post("/api/course/restart")
def api_course_restart():
    chat_id = (request.get_json(silent=True) or {}).get("chat_id") or request.args.get("chat_id", "default")
    try: return jsonify({"success": True, "progress": start_new_course(chat_id)})
    except ValueError as e: return jsonify({"success": False, "message": str(e)}), 400

@app.get("/api/course-history")
def api_course_history(): return jsonify({"items": list_course_snapshots(request.args.get("chat_id", "default"))})

@app.route("/api/custom-words", methods=["GET", "POST", "OPTIONS"])
def api_custom_words():
    if request.method == "OPTIONS": return "", 204
    data = request.get_json(silent=True) or {}; chat_id = request.args.get("chat_id") or data.get("chat_id")
    if not chat_id: return jsonify({"success": False, "message": "chat_id обязателен"}), 400
    if request.method == "GET":
        if request.args.get("all") == "1": return jsonify({"items": list_all_custom_words(chat_id)})
        return jsonify(list_custom_words(chat_id, request.args.get("page", 1, type=int) or 1, min(max(request.args.get("per_page", 10, type=int) or 10, 1), 50)))
    en = str(data.get("en", "")).strip(); ru = str(data.get("ru", "")).strip()
    if not en or not ru: return jsonify({"success": False, "message": "Заполни оба поля"}), 400
    return jsonify({"success": True, "item": add_custom_word(chat_id, en, ru)}), 201

@app.route("/api/custom-word", methods=["POST"])
def api_add_custom_word():
    data=request.get_json(silent=True) or {}; en=str(data.get("en","")).strip(); ru=str(data.get("ru","")).strip(); chat_id=data.get("chat_id","default")
    if not en or not ru: return jsonify({"success":False,"message":"Заполни оба поля"}),400
    return jsonify({"success":True,"item":add_custom_word(chat_id,en,ru)})

@app.route("/api/custom-word/<int:word_id>", methods=["PATCH", "DELETE", "OPTIONS"])
def api_manage_custom_word(word_id):
    if request.method == "OPTIONS": return "",204
    data=request.get_json(silent=True) or {}; chat_id=request.args.get("chat_id") or data.get("chat_id")
    try:
        if request.method=="DELETE": delete_custom_word(chat_id,word_id); return jsonify({"success":True})
        return jsonify({"success":True,"item":update_custom_word(chat_id,word_id,str(data.get("en","")).strip(),str(data.get("ru","")).strip())})
    except ValueError as e: return jsonify({"success":False,"message":str(e)}),404

@app.route("/api/link-chat-id", methods=["POST", "OPTIONS"])
def api_link_chat_id():
    if request.method=="OPTIONS": return "",204
    data=request.get_json(silent=True) or {}
    try: return jsonify({"success":True, **bind_chat_ids(data.get("site_chat_id",""), data.get("telegram_chat_id",""))})
    except ValueError as e: return jsonify({"success":False,"message":str(e)}),400

@app.get("/api/health")
def api_health(): return jsonify({"status":"ok"})
@app.get("/api/help")
def api_help(): return jsonify({"title":"📚 Помощь по English Learning","description":"Приложение для изучения 300 самых популярных английских существительных."})

if __name__ == "__main__": app.run(host="0.0.0.0", port=5000)
