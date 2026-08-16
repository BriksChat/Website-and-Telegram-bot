"""SQL-backed domain operations shared by the REST API."""
import json

from app.database import Card, ChatIdAlias, CompletedCard, CourseSnapshot, CustomWord, HardWord, UserProgress, Word, db
from app.seed_data import CARDS


def initialize_database():
    db.create_all()
    if Card.query.first() is None:
        for item in CARDS:
            card = Card(id=item["id"])
            card.words = [Word(en=w["en"], ru=w["ru"]) for w in item["words"]]
            db.session.add(card)
        db.session.commit()


def resolve_chat_id(chat_id):
    value = str(chat_id).strip()
    if not value or len(value) > 64:
        raise ValueError("Некорректный chat_id")
    alias = ChatIdAlias.query.filter_by(alias_chat_id=value).first()
    return alias.canonical_chat_id if alias else value


def _user(chat_id):
    value = resolve_chat_id(chat_id)
    user = UserProgress.query.filter_by(chat_id=value).first()
    if user is None:
        user = UserProgress(chat_id=value)
        db.session.add(user)
        db.session.commit()
    return user


def load_words():
    return {"cards": [{"id": card.id, "words": [{"en": w.en, "ru": w.ru} for w in card.words]} for card in Card.query.order_by(Card.id).all()]}


def list_dictionary(page=1, per_page=10):
    query = Word.query.join(Card, Word.card_id == Card.id).filter(Card.id != 99).order_by(Card.id, Word.id)
    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {"items": [{"id": i.id, "card_id": i.card_id, "en": i.en, "ru": i.ru} for i in items], "page": page, "per_page": per_page, "total": total, "total_pages": total_pages, "read_only": True}


def get_total_cards():
    return Card.query.filter(Card.id != 99).count()


def _hard_word_stats(user):
    translations = {item.en.casefold(): item.ru for item in Word.query.order_by(Word.id).all()}
    items = HardWord.query.filter_by(user_id=user.id).order_by(HardWord.mistakes.desc(), HardWord.id.asc()).all()
    return [{"en": item.word_en, "ru": translations.get(item.word_en.casefold(), ""), "mistakes": item.mistakes} for item in items]


def _snapshot_payload(item):
    total = item.total_correct + item.total_wrong
    return {"id": item.id, "course_number": item.course_number, "total_correct": item.total_correct, "total_wrong": item.total_wrong, "accuracy": round(item.total_correct / total * 100, 1) if total else 0, "best_streak": item.best_streak, "hard_word_stats": json.loads(item.hard_words_json or "[]"), "completed_at": item.completed_at.isoformat() if item.completed_at else None}


def list_course_snapshots(chat_id):
    user = _user(chat_id)
    return [_snapshot_payload(item) for item in CourseSnapshot.query.filter_by(user_id=user.id).order_by(CourseSnapshot.course_number.desc()).all()]


def snapshot_current_course(chat_id):
    user = _user(chat_id)
    if not user.finished:
        raise ValueError("Текущий курс ещё не завершён")
    existing = CourseSnapshot.query.filter_by(user_id=user.id).count()
    item = CourseSnapshot(user_id=user.id, course_number=existing + 1, total_correct=user.total_correct, total_wrong=user.total_wrong, best_streak=user.best_streak, hard_words_json=json.dumps(_hard_word_stats(user), ensure_ascii=False))
    db.session.add(item)
    db.session.flush()
    return item


def start_new_course(chat_id):
    user = _user(chat_id)
    if not user.finished:
        raise ValueError("Новый курс можно начать после завершения текущего")
    snapshot_current_course(chat_id)
    CompletedCard.query.filter_by(user_id=user.id).delete()
    HardWord.query.filter_by(user_id=user.id).delete()
    user.current_card = 1
    user.total_correct = 0
    user.total_wrong = 0
    user.streak = 0
    user.best_streak = 0
    user.finished = False
    db.session.commit()
    return load_progress(chat_id)


def load_progress(chat_id):
    user = _user(chat_id)
    completed = [item.card_id for item in CompletedCard.query.filter_by(user_id=user.id).order_by(CompletedCard.card_id)]
    hard_stats = _hard_word_stats(user)
    custom = [{"id": item.id, "en": item.en, "ru": item.ru} for item in CustomWord.query.filter_by(user_id=user.id).order_by(CustomWord.id).all()]
    return {"current_card": user.current_card, "completed_cards": completed, "total_correct": user.total_correct, "total_wrong": user.total_wrong, "streak": user.streak, "best_streak": user.best_streak, "hard_words": [item["en"] for item in hard_stats], "hard_word_stats": hard_stats, "finished": user.finished, "custom_words": custom, "course_number": CourseSnapshot.query.filter_by(user_id=user.id).count() + 1}


def save_progress(chat_id, progress):
    user = _user(chat_id)
    for name in ("current_card", "total_correct", "total_wrong", "streak", "best_streak", "finished"):
        if name in progress:
            setattr(user, name, progress[name])
    if "completed_cards" in progress:
        CompletedCard.query.filter_by(user_id=user.id).delete()
        for card_id in sorted(set(progress["completed_cards"])):
            db.session.add(CompletedCard(user_id=user.id, card_id=card_id))
    db.session.commit()


def add_hard_word(chat_id, word_en):
    user = _user(chat_id)
    item = HardWord.query.filter_by(user_id=user.id, word_en=word_en).first()
    if item:
        item.mistakes += 1
    else:
        db.session.add(HardWord(user_id=user.id, word_en=word_en))
    db.session.commit()


def list_custom_words(chat_id, page=1, per_page=10):
    user = _user(chat_id)
    query = CustomWord.query.filter_by(user_id=user.id).order_by(CustomWord.id)
    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {"items": [{"id": i.id, "en": i.en, "ru": i.ru} for i in items], "page": page, "per_page": per_page, "total": total, "total_pages": total_pages}


def list_all_custom_words(chat_id):
    user = _user(chat_id)
    return [{"id": i.id, "en": i.en, "ru": i.ru} for i in CustomWord.query.filter_by(user_id=user.id).order_by(CustomWord.id).all()]


def add_custom_word(chat_id, en_word, ru_word):
    user = _user(chat_id)
    item = CustomWord(user_id=user.id, en=en_word.strip(), ru=ru_word.strip())
    db.session.add(item); db.session.commit()
    return {"id": item.id, "en": item.en, "ru": item.ru}


def update_custom_word(chat_id, word_id, en_word, ru_word):
    user = _user(chat_id); item = CustomWord.query.filter_by(id=word_id, user_id=user.id).first()
    if item is None: raise ValueError("Личное слово не найдено")
    item.en = en_word.strip(); item.ru = ru_word.strip(); db.session.commit()
    return {"id": item.id, "en": item.en, "ru": item.ru}


def delete_custom_word(chat_id, word_id):
    user = _user(chat_id); item = CustomWord.query.filter_by(id=word_id, user_id=user.id).first()
    if item is None: raise ValueError("Личное слово не найдено")
    db.session.delete(item); db.session.commit()


def bind_chat_ids(site_chat_id, telegram_chat_id):
    site_value, telegram_value = str(site_chat_id).strip(), str(telegram_chat_id).strip()
    if not site_value.isdigit() or not telegram_value.isdigit(): raise ValueError("Chat_ID должен содержать только цифры")
    canonical = UserProgress.query.filter_by(chat_id=telegram_value).first()
    if canonical is None:
        canonical = UserProgress(chat_id=telegram_value); db.session.add(canonical); db.session.flush()
    source = UserProgress.query.filter_by(chat_id=site_value).first()
    if source is not None and source.id != canonical.id:
        canonical.current_card = max(canonical.current_card, source.current_card); canonical.total_correct += source.total_correct; canonical.total_wrong += source.total_wrong; canonical.best_streak = max(canonical.best_streak, source.best_streak); canonical.finished = canonical.finished or source.finished
        existing_cards = {i.card_id for i in CompletedCard.query.filter_by(user_id=canonical.id)}
        for i in CompletedCard.query.filter_by(user_id=source.id).all():
            if i.card_id not in existing_cards: db.session.add(CompletedCard(user_id=canonical.id, card_id=i.card_id))
        for i in CustomWord.query.filter_by(user_id=source.id).all(): db.session.add(CustomWord(user_id=canonical.id, en=i.en, ru=i.ru))
        for snap in CourseSnapshot.query.filter_by(user_id=source.id).order_by(CourseSnapshot.course_number).all():
            snap.user_id = canonical.id; snap.course_number = CourseSnapshot.query.filter_by(user_id=canonical.id).count() + 1
        CompletedCard.query.filter_by(user_id=source.id).delete(); HardWord.query.filter_by(user_id=source.id).delete(); CustomWord.query.filter_by(user_id=source.id).delete(); db.session.delete(source)
    alias = ChatIdAlias.query.filter_by(alias_chat_id=site_value).first()
    if alias is None: db.session.add(ChatIdAlias(alias_chat_id=site_value, canonical_chat_id=telegram_value))
    else: alias.canonical_chat_id = telegram_value
    db.session.commit(); return {"site_chat_id": site_value, "telegram_chat_id": telegram_value}
