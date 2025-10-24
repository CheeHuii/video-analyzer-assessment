# backend/db.py
import json
import sqlite3
from typing import List, Optional
import time
import uuid
from dataclasses import dataclass

DB_PATH = "data/chat_history.db"  # commit .gitignore or allow example

def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = _conn()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS conversations (
      id TEXT PRIMARY KEY,
      title TEXT,
      created_at INTEGER
    );
    CREATE TABLE IF NOT EXISTS messages (
      id TEXT PRIMARY KEY,
      conversation_id TEXT NOT NULL,
      sender TEXT NOT NULL,
      text TEXT,
      created_at INTEGER,
      confidence REAL DEFAULT NULL,
      needs_clarification INTEGER DEFAULT 0,
      attachments_json TEXT DEFAULT '[]',
      metadata_json TEXT DEFAULT '{}',
      FOREIGN KEY(conversation_id) REFERENCES conversations(id)
    );
    CREATE TABLE IF NOT EXISTS attachments (
      id TEXT PRIMARY KEY,
      message_id TEXT NOT NULL,
      filename TEXT,
      path TEXT,
      mime_type TEXT,
      created_at INTEGER,
      FOREIGN KEY(message_id) REFERENCES messages(id)
    );
    """)
    conn.commit()
    conn.close()

def now_ms():
    return int(time.time() * 1000)

def ensure_conversation(conversation_id: str, title: Optional[str] = None):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,))
    r = cur.fetchone()
    if not r:
        cur.execute("INSERT INTO conversations (id, title, created_at) VALUES (?, ?, ?)",
                    (conversation_id, title or "", now_ms()))
        conn.commit()
    conn.close()

def store_message(message: dict):
    """
    message: dict with keys id, conversation_id, sender, text, created_at, confidence, needs_clarification, attachments (list), metadata_json
    """
    conn = _conn()
    cur = conn.cursor()
    ensure_conversation(message["conversation_id"])
    cur.execute("""
      INSERT INTO messages(id, conversation_id, sender, text, created_at, confidence, needs_clarification, attachments_json, metadata_json)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        message["id"],
        message["conversation_id"],
        message["sender"],
        message.get("text"),
        message.get("created_at", now_ms()),
        message.get("confidence"),
        1 if message.get("needs_clarification") else 0,
        json.dumps(message.get("attachments", [])),
        json.dumps(message.get("metadata_json", {}))
    ))
    conn.commit()
    conn.close()

def get_history(conversation_id: str, limit: int = 100, offset: int = 0):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
      SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ? OFFSET ?
    """, (conversation_id, limit, offset))
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            "id": r["id"],
            "conversation_id": r["conversation_id"],
            "sender": r["sender"],
            "text": r["text"],
            "created_at": r["created_at"],
            "confidence": r["confidence"],
            "needs_clarification": bool(r["needs_clarification"]),
            "attachments": json.loads(r["attachments_json"]),
            "metadata_json": json.loads(r["metadata_json"])
        })
    return result
