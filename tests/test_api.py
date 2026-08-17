import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "english_learning"))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ADMIN_PASSWORD"] = "test-admin-password"
os.environ.pop("TELEGRAM_BOT_TOKEN", None)

from app.server import app


class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config.update(TESTING=True)
        cls.client = app.test_client()

    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_seed_contains_300_main_words(self):
        response = self.client.get("/api/all-words")
        self.assertEqual(response.status_code, 200)
        cards = response.get_json()["cards"]
        main_words = [
            word
            for card in cards
            if card["id"] != 99
            for word in card["words"]
        ]
        self.assertEqual(len(main_words), 300)

    def test_hard_word_route_used_by_telegram_bot(self):
        response = self.client.post(
            "/api/hard-word",
            json={"chat_id": "90001", "word_en": "apple"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"success": True})

        progress = self.client.get("/api/progress?chat_id=90001").get_json()
        self.assertIn("apple", progress["hard_words"])

    def test_admin_login_and_dictionary_access(self):
        login = self.client.post(
            "/api/admin/login",
            json={"password": "test-admin-password"},
        )
        self.assertEqual(login.status_code, 200)

        words = self.client.get(
            "/api/admin/words",
            headers={"X-Admin-Password": "test-admin-password"},
        )
        self.assertEqual(words.status_code, 200)
        self.assertGreater(words.get_json()["total"], 0)

    def test_missing_hard_word_fields_are_rejected(self):
        response = self.client.post("/api/hard-word", json={})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
