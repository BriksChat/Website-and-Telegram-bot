"""HTTPS client used by the Telegram bot to access the shared REST API."""
import os
import requests

API_URL = os.environ.get("API_URL", "http://127.0.0.1:5000").rstrip("/")


def _request(method, path, **kwargs):
    response = requests.request(method, f"{API_URL}{path}", timeout=15, **kwargs)
    response.raise_for_status()
    return response.json()


def load_words():
    return _request("GET", "/api/all-words")


def get_total_cards():
    return len([card for card in load_words()["cards"] if card["id"] != 99])


def load_progress(chat_id):
    return _request("GET", "/api/progress", params={"chat_id": chat_id})


def save_progress(chat_id, progress):
    return _request("PUT", "/api/progress", json={"chat_id": str(chat_id), **progress})


def add_hard_word(chat_id, word_en):
    return _request("POST", "/api/hard-word", json={"chat_id": str(chat_id), "word_en": word_en})


def list_custom_words(chat_id, page=1, per_page=10):
    return _request(
        "GET",
        "/api/custom-words",
        params={"chat_id": str(chat_id), "page": page, "per_page": per_page},
    )


def add_custom_word(chat_id, en_word, ru_word):
    return _request(
        "POST",
        "/api/custom-words",
        json={"chat_id": str(chat_id), "en": en_word, "ru": ru_word},
    )


def update_custom_word(chat_id, word_id, en_word, ru_word):
    return _request(
        "PATCH",
        f"/api/custom-word/{word_id}",
        json={"chat_id": str(chat_id), "en": en_word, "ru": ru_word},
    )


def delete_custom_word(chat_id, word_id):
    return _request(
        "DELETE",
        f"/api/custom-word/{word_id}",
        json={"chat_id": str(chat_id)},
    )


def bind_chat_ids(site_chat_id, telegram_chat_id):
    return _request(
        "POST",
        "/api/link-chat-id",
        json={
            "site_chat_id": str(site_chat_id),
            "telegram_chat_id": str(telegram_chat_id),
        },
    )
