import sqlite3
import os
from config import DATABASE_PATH


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            emoji TEXT DEFAULT '💕',
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            caption TEXT,
            filename TEXT NOT NULL,
            thumbnail TEXT,
            media_type TEXT NOT NULL CHECK(media_type IN ('image', 'video')),
            category_id INTEGER,
            memory_date DATE,
            uploaded_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS letters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            is_private INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_memories_date ON memories(memory_date);
        CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category_id);
        CREATE INDEX IF NOT EXISTS idx_letters_created ON letters(created_at);
    """)

    # Insert default categories if empty
    cursor = conn.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        default_categories = [
            ("First Dates", "🥰", 1),
            ("Trips & Adventures", "✈️", 2),
            ("Daily Life", "☀️", 3),
            ("Special Days", "🎉", 4),
            ("Funny Moments", "😂", 5),
            ("Food & Drinks", "🍕", 6),
            ("Selfies", "🤳", 7),
            ("Uncategorized", "📁", 99),
        ]
        conn.executemany(
            "INSERT INTO categories (name, emoji, sort_order) VALUES (?, ?, ?)",
            default_categories,
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
