"""Database models and transactional persistence for the shared application."""
import os
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint


db = SQLAlchemy()


class UserProgress(db.Model):
    __tablename__ = "user_progress"
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    current_card = db.Column(db.Integer, nullable=False, default=1)
    total_correct = db.Column(db.Integer, nullable=False, default=0)
    total_wrong = db.Column(db.Integer, nullable=False, default=0)
    streak = db.Column(db.Integer, nullable=False, default=0)
    best_streak = db.Column(db.Integer, nullable=False, default=0)
    finished = db.Column(db.Boolean, nullable=False, default=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class CourseSnapshot(db.Model):
    """Immutable statistics for one completed pass through the main 300-word course."""
    __tablename__ = "course_snapshots"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user_progress.id", ondelete="CASCADE"), nullable=False, index=True)
    course_number = db.Column(db.Integer, nullable=False)
    total_correct = db.Column(db.Integer, nullable=False, default=0)
    total_wrong = db.Column(db.Integer, nullable=False, default=0)
    best_streak = db.Column(db.Integer, nullable=False, default=0)
    hard_words_json = db.Column(db.Text, nullable=False, default="[]")
    completed_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint("user_id", "course_number"),)


class ChatIdAlias(db.Model):
    """Maps a site-generated Chat_ID to the canonical Telegram Chat_ID."""
    __tablename__ = "chat_id_aliases"
    id = db.Column(db.Integer, primary_key=True)
    alias_chat_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    canonical_chat_id = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class Card(db.Model):
    __tablename__ = "cards"
    id = db.Column(db.Integer, primary_key=True)
    words = db.relationship("Word", backref="card", cascade="all, delete-orphan", order_by="Word.id")


class Word(db.Model):
    __tablename__ = "words"
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey("cards.id", ondelete="CASCADE"), nullable=False, index=True)
    en = db.Column(db.String(120), nullable=False)
    ru = db.Column(db.String(255), nullable=False)


class CompletedCard(db.Model):
    __tablename__ = "completed_cards"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user_progress.id", ondelete="CASCADE"), nullable=False)
    card_id = db.Column(db.Integer, db.ForeignKey("cards.id", ondelete="CASCADE"), nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "card_id"),)


class HardWord(db.Model):
    __tablename__ = "hard_words"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user_progress.id", ondelete="CASCADE"), nullable=False)
    word_en = db.Column(db.String(120), nullable=False)
    mistakes = db.Column(db.Integer, nullable=False, default=1)
    __table_args__ = (UniqueConstraint("user_id", "word_en"),)


class CustomWord(db.Model):
    __tablename__ = "custom_words"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user_progress.id", ondelete="CASCADE"), nullable=False)
    en = db.Column(db.String(120), nullable=False)
    ru = db.Column(db.String(255), nullable=False)


def configure_database(app):
    """Configure MySQL from DATABASE_URL (SQLite is used only for local development/tests)."""
    url = os.getenv("DATABASE_URL", "sqlite:///english_learning.db")
    if url.startswith("mysql://"):
        url = url.replace("mysql://", "mysql+pymysql://", 1)
    app.config.update(SQLALCHEMY_DATABASE_URI=url, SQLALCHEMY_TRACK_MODIFICATIONS=False)
    db.init_app(app)
