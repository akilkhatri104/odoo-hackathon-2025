import os
from dotenv import load_dotenv

load_dotenv()

from databases import Database
from sqlalchemy import (
    Table, Column, Integer, BigInteger, String, Text, Boolean,
    TIMESTAMP, Enum, ForeignKey, MetaData, ARRAY
)
import enum

DATABASE_URL = os.environ.get("DATABASE_URL")

metadata = MetaData()

class UserRole(enum.Enum):
    guest = "guest"
    user = "user"
    admin = "admin"

class NotificationType(enum.Enum):
    answer = "answer"
    comment = "comment"
    mention = "mention"

Users = Table(
    "users", metadata,
    Column("user_id", BigInteger, primary_key=True, autoincrement=True),
    Column("username", String(50), unique=True, nullable=False),
    Column("email", String(255), unique=True, nullable=False),
    Column("password_hash", String(255), nullable=False),
    Column("role", Enum(UserRole, name="user_role"), nullable=False, default=UserRole.user),
    Column("created_at", TIMESTAMP, nullable=False),
    Column("is_banned", Boolean, nullable=False, default=False)
)

Questions = Table(
    "questions", metadata,
    Column("question_id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, ForeignKey("Users.user_id"), nullable=False),
    Column("title", String(255), nullable=False),
    Column("description", Text, nullable=False),
    Column("tags", ARRAY(Text), nullable=False),
    Column("created_at", TIMESTAMP, nullable=False),
    Column("updated_at", TIMESTAMP)
)

Answers = Table(
    "answers", metadata,
    Column("answer_id", BigInteger, primary_key=True, autoincrement=True),
    Column("question_id", BigInteger, ForeignKey("Questions.question_id"), nullable=False),
    Column("user_id", BigInteger, ForeignKey("Users.user_id"), nullable=False),
    Column("description", Text, nullable=False),
    Column("img_url", String(255)),
    Column("tags", ARRAY(Text), nullable=False),
    Column("upvotes", Integer, nullable=False, default=0),
    Column("downvotes", Integer, nullable=False, default=0),
    Column("is_accepted", Boolean, nullable=False, default=False),
    Column("created_at", TIMESTAMP, nullable=False),
    Column("updated_at", TIMESTAMP)
)

Notifications = Table(
    "notifications", metadata,
    Column("notification_id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, ForeignKey("Users.user_id"), nullable=False),
    Column("type", Enum(NotificationType, name="notification_type"), nullable=False),
    Column("related_id", BigInteger, nullable=False),
    Column("message", String(255), nullable=False),
    Column("is_read", Boolean, nullable=False, default=False),
    Column("created_at", TIMESTAMP, nullable=False)
)


database = Database(DATABASE_URL)